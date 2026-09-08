import os
from typing import Optional, Any
from praxis_ai_gateway.providers.openai import OpenAIProvider
from praxis_ai_gateway.base import ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation

class XAIProvider(OpenAIProvider):
    name = "xai"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key or os.environ.get("XAI_API_KEY"))
        self.api_url = "https://api.x.ai/v1"

    def capabilities(self) -> ProviderCapabilities:
        if not self.api_key:
            return ProviderCapabilities(
                streaming=False, structured_output=False, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=0, is_local=False, is_free_tier=False
            )
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=True,
            embeddings=False,
            realtime_audio=False,
            max_context_tokens=128000,
            is_local=False,
            is_free_tier=False
        )
