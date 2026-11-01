import pytest
import httpx
import respx
from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError
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
@pytest.mark.asyncio
@respx.mock
async def test_openai_openrouter_base_url(messages, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-3.5-turbo")
    provider = OpenAIProvider(api_key="sk-or-test-key")
    
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "OpenRouter response"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 6}
        })
    )
    
    resp = await provider.generate(messages)
    assert resp.text == "OpenRouter response"
    assert resp.model == "openai/gpt-3.5-turbo"
    assert route.called
    req = route.calls.last.request
    assert req.headers["authorization"] == "Bearer sk-or-test-key"
    assert req.headers.get("http-referer") == "https://praxis-interview.com"


@pytest.mark.asyncio
@respx.mock
async def test_deepseek_openrouter_base_url(messages, monkeypatch):
    from praxis_ai_gateway.providers.deepseek import DeepSeekProvider
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat")
    provider = DeepSeekProvider(api_key="sk-or-deepseek-key")
    
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "DeepSeek OpenRouter response"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8}
        })
    )
    
    resp = await provider.generate(messages)
    assert resp.text == "DeepSeek OpenRouter response"
    assert resp.model == "deepseek/deepseek-chat"
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_gemini_google_api_key_fallback(messages, monkeypatch):
    from praxis_ai_gateway.providers.gemini import GeminiProvider
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
    
    provider = GeminiProvider()
    assert provider.api_key == "test-google-key"
    
    route = respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent").mock(
        return_value=httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10}
        })
    )
    
    resp = await provider.generate(messages)
    assert resp.text == "Gemini response"
    assert route.called
