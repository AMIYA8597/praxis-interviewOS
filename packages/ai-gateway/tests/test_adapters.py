import pytest
import httpx
import respx
from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderServerError
from praxis_ai_gateway.providers.openai import OpenAIProvider
from praxis_ai_gateway.providers.groq import GroqProvider

@pytest.fixture
def messages():
    return [LLMMessage(role="user", content="Hello")]

@pytest.mark.asyncio
@respx.mock
async def test_openai_generate_success(messages):
    provider = OpenAIProvider(api_key="test-key")
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "Hi there!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        })
    )
    
    resp = await provider.generate(messages, model="gpt-4o-mini")
    assert resp.text == "Hi there!"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.provider == "openai"

@pytest.mark.asyncio
@respx.mock
async def test_openai_generate_auth_error(messages):
    provider = OpenAIProvider(api_key="test-key")
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": "invalid api key"})
    )
    
    with pytest.raises(ProviderAuthError):
        await provider.generate(messages)

@pytest.mark.asyncio
@respx.mock
async def test_groq_rate_limit(messages):
    provider = GroqProvider(api_key="test-key")
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate limit exceeded"})
    )
    
    with pytest.raises(ProviderRateLimitError):
        await provider.generate(messages)
