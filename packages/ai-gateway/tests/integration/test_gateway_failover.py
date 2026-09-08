import pytest
import fakeredis.aioredis
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import yaml

from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext, RoutedCall, AllProvidersUnavailableError
from praxis_ai_gateway.base import LLMMessage, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.errors import ProviderServerError

class FakeProvider:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
        
    def capabilities(self):
        return ProviderCapabilities(
            streaming=False, structured_output=False, vision=False, embeddings=False,
            realtime_audio=False, max_context_tokens=8192, is_local=self.name=="ollama", is_free_tier=True
        )
        
    async def generate(self, messages, cancellation_token=None, **kw):
        self.call_count += 1
        if self.should_fail:
            raise ProviderServerError(f"{self.name} failed")
        return LLMResponse(text=f"Hello from {self.name}", latency_ms=10.0, model=kw.get("model", "fake"), provider=self.name)

@pytest.fixture
def registry(tmp_path):
    config = {
        "aliases": {
            "demo_task": [
                {"provider": "groq", "model": "llama-3"},
                {"provider": "ollama", "model": "llama-3"},
            ]
        }
    }
    config_file = tmp_path / "models.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return ModelRegistry(config_file)

@pytest.mark.asyncio
async def test_gateway_failover(registry):
    redis = fakeredis.aioredis.FakeRedis()
    db = AsyncMock()
    
    groq = FakeProvider("groq", should_fail=True)
    ollama = FakeProvider("ollama", should_fail=False)
    
    providers = {"groq": groq, "ollama": ollama}
    router = GatewayRouter(registry, providers, redis, db)

    context = RoutingContext(user_id="test")
    
    # 1. Groq is preferred (listed first). 
    # Force 5 consecutive failures by making 2 routed calls (each attempts 3 times due to retries).
    # Call 1: groq (attempt 1 fail, attempt 2 fail, attempt 3 fail -> exhausted). Router falls back to ollama.
    res1 = await router.route("demo_task", context, "generate", [])
    assert res1.provider_name == "ollama"
    assert groq.call_count == 3
    assert ollama.call_count == 1
    
    # Call 2: groq circuit breaker is OPEN now? 
    # Wait, max_failures=5. The first call caused 3 failures.
    # Second call attempts groq: attempt 1 fail, attempt 2 fail -> total 5 failures -> circuit breaker transitions to OPEN.
    # GatewayExhaustedError thrown. Router falls back to ollama.
    res2 = await router.route("demo_task", context, "generate", [])
    assert res2.provider_name == "ollama"
    assert groq.call_count == 6  # Call 1 (3 attempts) + Call 2 (3 attempts). Breaker opens at 5, but retry loop finishes its tries.
    # Actually `with_retries` checks `can_execute()` at the top. Once `record_failure` pushes to 5, the NEXT call fails `can_execute()`.
    
    # Call 3: Groq's breaker is OPEN. It should be skipped entirely.
    groq_calls_before = groq.call_count
    res3 = await router.route("demo_task", context, "generate", [])
    assert res3.provider_name == "ollama"
    assert groq.call_count == groq_calls_before # NO NEW CALLS TO GROQ
    
    # Check that model_requests logged the fallback
    assert db.execute.call_count >= 3
    
    # Wait past cooldown... FakeRedis doesn't auto-expire keys with time unless we sleep or mock.
    # Let's manually delete the state key or let it expire to simulate cooldown.
    await redis.delete("cb:state:groq:generate")
    
    # Make Groq succeed now
    groq.should_fail = False
    
    # Call 4: Breaker is HALF_OPEN (expired). Exactly one probe should happen and succeed -> CLOSED.
    res4 = await router.route("demo_task", context, "generate", [])
    assert res4.provider_name == "groq"
    assert groq.call_count == groq_calls_before + 1
    
    # Call 5: Breaker is CLOSED, Groq stays preferred.
    res5 = await router.route("demo_task", context, "generate", [])
    assert res5.provider_name == "groq"

@pytest.mark.asyncio
async def test_cancellation_propagation(registry):
    redis = fakeredis.aioredis.FakeRedis()
    db = AsyncMock()
    
    class SlowProvider:
        name = "slow"
        def capabilities(self): return ProviderCapabilities(is_local=False, is_free_tier=True, streaming=False, structured_output=False, vision=False, embeddings=False, realtime_audio=False, max_context_tokens=100)
        async def generate(self, messages, cancellation_token=None, **kw):
            # Simulate a slow retry process
            raise ProviderServerError("Simulated server error")
            
    registry._aliases["demo_task"] = [{"provider": "slow", "model": "test"}]
    providers = {"slow": SlowProvider()}
    router = GatewayRouter(registry, providers, redis, db)
    
    from praxis_ai_gateway.cancellation import CancellationToken
    token = CancellationToken()

    async def cancel_soon():
        await asyncio.sleep(0.1) # Cancel during the first backoff
        token.cancel("User cancelled")

    asyncio.create_task(cancel_soon())

    with pytest.raises(asyncio.CancelledError):
        await router.route("demo_task", RoutingContext(user_id="test"), "generate", [], cancellation_token=token)
