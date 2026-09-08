import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import yaml
import fakeredis.aioredis

from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext, RoutedCall
from praxis_ai_gateway.base import ProviderCapabilities, LLMResponse
from praxis_ai_gateway.budget import ConsentRequiredError

class FakeProvider:
    def __init__(self, name: str, is_free_tier: bool):
        self.name = name
        self.is_free_tier = is_free_tier
        self.call_count = 0
        
    def capabilities(self):
        return ProviderCapabilities(
            streaming=False, structured_output=False, vision=False, embeddings=False,
            realtime_audio=False, max_context_tokens=8192, is_local=False, is_free_tier=self.is_free_tier
        )
        
    async def generate(self, messages, cancellation_token=None, **kw):
        self.call_count += 1
        return LLMResponse(text=f"Hello from {self.name}", latency_ms=10.0, model=kw.get("model", "fake"), provider=self.name, input_tokens=100, output_tokens=100)

@pytest.fixture
def registry(tmp_path):
    config = {
        "aliases": {
            "reasoning": [
                {"provider": "openai", "model": "gpt-4o", "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015},
                {"provider": "groq", "model": "llama-3"},
            ]
        }
    }
    config_file = tmp_path / "models.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return ModelRegistry(config_file)

@pytest.mark.asyncio
async def test_budget_guard(registry):
    redis = fakeredis.aioredis.FakeRedis()
    db = AsyncMock()
    
    openai = FakeProvider("openai", is_free_tier=False)
    groq = FakeProvider("groq", is_free_tier=True)
    
    providers = {"openai": openai, "groq": groq}
    router = GatewayRouter(registry, providers, redis, db)
    
    # Test 1: ZERO_SPEND_MODE=True routes to free tier and avoids OpenAI
    ctx_free = RoutingContext(user_id="user_123", zero_spend_mode=True)
    res_free = await router.route("reasoning", ctx_free, "generate", [])
    
    assert res_free.provider_name == "groq"
    assert groq.call_count == 1
    assert openai.call_count == 0
    
    # Test 2: ZERO_SPEND_MODE=False, no consent
    ctx_paid = RoutingContext(user_id="user_123", zero_spend_mode=False)
    # Mock DB so check_consent fails: no prior spend, and no profile acknowledgement
    # Mocking usage_events check
    mock_result_usage = MagicMock()
    mock_result_usage.scalar.return_value = False
    
    # Mocking profiles check
    mock_result_prof = MagicMock()
    mock_result_prof.scalar.return_value = False
    
    db.execute.side_effect = [mock_result_usage, mock_result_prof]
    
    with pytest.raises(ConsentRequiredError):
        await router.route("reasoning", ctx_paid, "generate", [])
        
    assert openai.call_count == 0
    
    # Test 3: ZERO_SPEND_MODE=False, with consent
    # Let profiles check succeed
    mock_result_prof.scalar.return_value = True
    db.execute.side_effect = [mock_result_usage, mock_result_prof, MagicMock(), MagicMock()] # Subsequent calls for log_fallback and log_usage
    
    res_paid = await router.route("reasoning", ctx_paid, "generate", [])
    assert res_paid.provider_name == "openai"
    assert openai.call_count == 1
    
    # Verify spend was committed
    daily_spend = float(await redis.get("budget:daily:user_123:2026-09-08") or 0.0) # Might be UTC date, depends on runner.
    # Actually, we don't know the exact string, let's just check keys
    keys = await redis.keys("budget:daily:user_123:*")
    assert len(keys) == 1
    spend = float(await redis.get(keys[0]))
    assert spend == 0.002 # 100 in, 100 out * cost (0.005/k, 0.015/k) = 0.0005 + 0.0015 = 0.002
