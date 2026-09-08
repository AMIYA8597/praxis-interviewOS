import pytest
import yaml
from pathlib import Path

from praxis_ai_gateway.base import ProviderCapabilities, LLMProvider, LLMMessage, LLMDelta, LLMResponse
from praxis_ai_gateway.registry import ModelRegistry, ConfigurationError

class MockProvider:
    def __init__(self, name: str, capabilities: ProviderCapabilities):
        self.name = name
        self._caps = capabilities
        
    async def generate(self, *args, **kw) -> LLMResponse: pass
    async def stream(self, *args, **kw): pass
    async def structured(self, *args, **kw): pass
    async def embed(self, *args, **kw): pass
    
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

@pytest.fixture
def mock_config(tmp_path):
    config = {
        "aliases": {
            "test_task": [
                {"provider": "local_mock", "model": "local-model-v1", "max_latency_ms": 500},
                {"provider": "free_cloud", "model": "free-model-v1", "max_latency_ms": 1000},
                {"provider": "paid_cloud", "model": "paid-model-v1", "max_latency_ms": 2000},
            ]
        }
    }
    config_file = tmp_path / "models.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file

@pytest.fixture
def providers():
    return {
        "local_mock": MockProvider(
            "local_mock",
            ProviderCapabilities(
                streaming=True, structured_output=True, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=8192, is_local=True, is_free_tier=True
            )
        ),
        "free_cloud": MockProvider(
            "free_cloud",
            ProviderCapabilities(
                streaming=True, structured_output=False, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=16000, is_local=False, is_free_tier=True
            )
        ),
        "paid_cloud": MockProvider(
            "paid_cloud",
            ProviderCapabilities(
                streaming=True, structured_output=True, vision=True, embeddings=True, 
                realtime_audio=True, max_context_tokens=128000, is_local=False, is_free_tier=False
            )
        )
    }

def test_verify_at_build_raises(tmp_path):
    config = {
        "aliases": {
            "unverified_task": [
                {"provider": "openai", "model": "gpt-<VERIFY_AT_BUILD>"}
            ]
        }
    }
    config_file = tmp_path / "models.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
        
    with pytest.raises(ConfigurationError, match="<VERIFY_AT_BUILD>"):
        ModelRegistry(config_file)

@pytest.mark.parametrize("local_only, req_caps, expected_providers", [
    # local_only=True excludes both cloud mocks
    (True, None, ["local_mock"]),
    
    # local_only=False, ZERO_SPEND_MODE-equivalent (is_free_tier=True) excludes paid mock
    (False, {"is_free_tier": True}, ["local_mock", "free_cloud"]),
    
    # vision-required task excludes local_mock and free_cloud
    (False, {"vision": True}, ["paid_cloud"]),
    
    # structured_output=True excludes free_cloud
    (False, {"structured_output": True}, ["local_mock", "paid_cloud"]),
])
def test_filter_candidates(mock_config, providers, local_only, req_caps, expected_providers):
    registry = ModelRegistry(mock_config)
    
    req_obj = None
    if req_caps:
        # Build dummy capabilities object with default falsy values, overriding requested
        caps_args = {
            "streaming": False, "structured_output": False, "vision": False, 
            "embeddings": False, "realtime_audio": False, "max_context_tokens": 0, 
            "is_local": False, "is_free_tier": False
        }
        caps_args.update(req_caps)
        req_obj = ProviderCapabilities(**caps_args)
        
    filtered = registry.filter_candidates(
        task="test_task", 
        providers=providers, 
        required_capabilities=req_obj, 
        local_only=local_only
    )
    
    returned_providers = [p.name for p, model in filtered]
    assert returned_providers == expected_providers
