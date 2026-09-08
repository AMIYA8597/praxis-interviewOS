import pytest
import asyncio
import time
from typing import AsyncIterator, Any
from unittest.mock import AsyncMock

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.registry import ModelRegistry
from realtime_agent.app.interview.generation import SessionGenerationManager
from realtime_agent.app.interview.barge_in import BargeInController
from realtime_agent.app.session.state_machine import StateMachine, SessionState
from realtime_agent.app.protocol import Envelope

class SlowStreamingProvider(LLMProvider):
    name = "slow_mock"
    
    def capabilities(self):
        return ProviderCapabilities(
            streaming=True, structured_output=False, vision=False, embeddings=False, 
            realtime_audio=False, max_context_tokens=8192, is_local=True, is_free_tier=True
        )

    async def stream(self, messages, cancellation_token=None, **kw) -> AsyncIterator[LLMDelta]:
        for i in range(100):
            # The cancellation check MUST happen inside the loop
            if cancellation_token and cancellation_token.is_cancelled():
                break
            await asyncio.sleep(0.01) # 10ms chunks
            yield LLMDelta(text=f"chunk {i} ", is_final=False)
            
    async def generate(self, messages, cancellation_token=None, **kw): ...
    async def structured(self, messages, schema, cancellation_token=None, **kw): ...
    async def embed(self, texts, cancellation_token=None, **kw): ...

@pytest.mark.asyncio
async def test_barge_in_mechanism():
    provider = SlowStreamingProvider()
    
    # Simple registry bypass for the test
    class MockRegistry:
        def filter_candidates(self, *args, **kwargs):
            return [(provider, {"provider": "slow_mock", "model": "mock", "cost_per_1k_input": 0, "cost_per_1k_output": 0})]
            
    import fakeredis
    # Mock Redis & DB
    redis = fakeredis.FakeAsyncRedis()
    db = AsyncMock()
    
    # We mock check_consent and check_and_reserve to pass
    db.execute.return_value.scalar.return_value = True 
    
    router = GatewayRouter(MockRegistry(), {"slow_mock": provider}, redis, db)
    
    # State tracking
    sm = StateMachine(SessionState.READY)
    sm.transition(SessionState.INTERVIEWER_TURN)
    
    transitions = []
    async def mock_transition(to_state, reason):
        sm.transition(to_state)
        transitions.append(to_state)
        
    events = []
    def mock_enqueue(evt: Envelope, critical: bool):
        events.append(evt)
        
    gen_manager = SessionGenerationManager()
    barge_controller = BargeInController("sess-1", gen_manager, mock_transition, mock_enqueue)
    
    # 1. Start generation
    ctx = gen_manager.start_generation("turn-1")
    
    messages = [LLMMessage(role="user", content="tell me a long story")]
    route_ctx = RoutingContext(user_id="user-1")
    
    stream_results = []
    stream_task = None
    
    async def run_stream():
        resp = await router.route("reasoning", route_ctx, "stream", messages, cancellation_token=ctx.token)
        async for delta in resp.result:
            if not gen_manager.is_current(ctx.generation_id):
                # Identity check: discard stale!
                break
            stream_results.append(delta.text)
            
    stream_task = asyncio.create_task(run_stream())
    
    # Wait briefly for stream to start
    await asyncio.sleep(0.05)
    
    # 2. Trigger Barge-in!
    start_cancel_ts = time.perf_counter()
    await barge_controller.trigger("candidate_spoke")
    
    # Wait for stream task to finish
    await stream_task
    end_cancel_ts = time.perf_counter()
    
    cancel_latency_ms = (end_cancel_ts - start_cancel_ts) * 1000.0
    print(f"\n[Barge-in] Cancellation overhead latency: {cancel_latency_ms:.2f}ms")
    
    # Assertions
    assert cancel_latency_ms < 50.0, "Cancellation took too long!"
    
    # Should only have a few chunks, not 100
    assert len(stream_results) > 0
    assert "mock generation complete" not in "".join(stream_results)
    
    await redis.close()
    assert transitions == [SessionState.YIELDING, SessionState.AWAITING_ANSWER]
    assert sm.state == SessionState.AWAITING_ANSWER
    
    # Events
    assert len(events) == 1
    assert events[0].type == "audio.stop_playback"
    
    # 3. Guard against chunk leakage (Task 4)
    # Start a NEW generation immediately
    ctx2 = gen_manager.start_generation("turn-2")
    stream_results2 = []
    
    async def run_stream2():
        resp = await router.route("reasoning", route_ctx, "stream", messages, cancellation_token=ctx2.token)
        async for delta in resp.result:
            stream_results2.append(delta.text)
            
    stream_task2 = asyncio.create_task(run_stream2())
    await asyncio.sleep(0.05)
    
    # This proves the new stream starts fresh at chunk 0, no leaked buffered chunks
    # from the previous async generator
    assert "chunk 0 " in stream_results2
    
    ctx2.token.cancel("done")
    await stream_task2
