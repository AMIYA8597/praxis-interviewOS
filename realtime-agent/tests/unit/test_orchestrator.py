import pytest
from unittest.mock import AsyncMock, MagicMock
from realtime_agent.app.session.orchestrator import SessionOrchestrator
from realtime_agent.app.session.manager import SessionManager
from realtime_agent.app.session.state_machine import SessionState
from realtime_agent.app.interview.policy import InterviewSession, PolicyDecision
from realtime_agent.app.interview.generation import SessionGenerationManager
from praxis_ai_gateway.router import GatewayRouter, RoutingContext

@pytest.mark.asyncio
async def test_begin_interviewer_turn():
    # 1. Setup mocks
    mock_sm = MagicMock(spec=SessionManager)
    mock_sm.transition = AsyncMock()

    mock_policy = MagicMock(spec=InterviewSession)
    fake_decision = PolicyDecision(is_clarifying_follow_up=False, response_text="Fake response text")
    mock_policy.generate_next_turn = AsyncMock(return_value=fake_decision)

    mock_gen_manager = MagicMock(spec=SessionGenerationManager)
    fake_gen_ctx = MagicMock()
    fake_gen_ctx.token.is_cancelled.return_value = False
    mock_gen_manager.start_generation.return_value = fake_gen_ctx

    mock_gateway = MagicMock(spec=GatewayRouter)
    mock_routing_ctx = MagicMock(spec=RoutingContext)

    mock_tts = MagicMock()
    
    async def fake_synthesize(text_iter, token):
        yield b"fake_audio_bytes"
    mock_tts.synthesize_streaming = fake_synthesize

    events = []
    def fake_enqueue(evt, critical=False):
        events.append(evt)

    # 2. Instantiate orchestrator
    orchestrator = SessionOrchestrator(
        session=mock_policy,
        generation_manager=mock_gen_manager,
        session_manager=mock_sm,
        gateway=mock_gateway,
        routing_ctx=mock_routing_ctx,
        tts=mock_tts,
        enqueue_event=fake_enqueue
    )
    # Ensure current_candidate_answer exists for policy to consume
    if not hasattr(orchestrator, "current_candidate_answer"):
        orchestrator.current_candidate_answer = "Candidate answer"

    # 3. Call method
    await orchestrator.begin_interviewer_turn(is_follow_up=False)

    # 4. Assertions
    # state machine transitioned
    mock_sm.transition.assert_any_call(SessionState.INTERVIEWER_TURN)
    
    # policy consulted
    mock_policy.generate_next_turn.assert_called_once()
    
    # generation started
    mock_gen_manager.start_generation.assert_called_once()
    
    # events enqueued correctly
    assert len(events) >= 2
    # Question text event first
    assert events[0].type == "interviewer.text"
    assert events[0].payload["text"] == "Fake response text"
    
    # Then audio chunks
    assert b"fake_audio_bytes" in events

    print("Test passed successfully. Output events:", events)
