import os
from typing import Optional, Any
from praxis_ai_gateway.providers.openai import OpenAIProvider
from praxis_ai_gateway.base import ProviderCapabilities, LLMMessage, LLMResponse
from pydantic import BaseModel

class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        url = base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        super().__init__(api_key=key, base_url=url)

    def capabilities(self) -> ProviderCapabilities:
        if not self.api_key:
            return ProviderCapabilities(
                streaming=False, structured_output=False, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=0, is_local=False, is_free_tier=False
            )
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=False,
            embeddings=False,
            realtime_audio=False,
            max_context_tokens=64000,
            is_local=False,
            is_free_tier=False
        )

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        if "model" not in kw and os.environ.get("DEEPSEEK_MODEL"):
            kw["model"] = os.environ["DEEPSEEK_MODEL"]
        return await super()._generate(messages, cancellation_token=cancellation_token, **kw)

    async def stream(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw):
        if "model" not in kw and os.environ.get("DEEPSEEK_MODEL"):
            kw["model"] = os.environ["DEEPSEEK_MODEL"]
        async for delta in super().stream(messages, cancellation_token=cancellation_token, **kw):
            yield delta

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        if "model" not in kw and os.environ.get("DEEPSEEK_MODEL"):
            kw["model"] = os.environ["DEEPSEEK_MODEL"]
        return await super()._structured(messages, schema, cancellation_token=cancellation_token, **kw)
