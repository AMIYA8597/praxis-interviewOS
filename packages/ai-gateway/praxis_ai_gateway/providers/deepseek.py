import os
from typing import Optional, Any
from praxis_ai_gateway.providers.openai import OpenAIProvider
from praxis_ai_gateway.base import ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation

class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key or os.environ.get("DEEPSEEK_API_KEY"))
        self.api_url = "https://api.deepseek.com"

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
