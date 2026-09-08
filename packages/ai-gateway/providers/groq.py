import os
from packages.ai_gateway.base import LLMProvider, ProviderCapabilities

class GroqProvider:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.api_key = os.environ.get("GROQ_API_KEY")

    def is_configured(self) -> bool:
        return self.api_key is not None

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=False,
            embeddings=False,
            realtime_audio=True, # Whisper
            max_context=8192,
            is_local=False,
            is_free_tier=True # Currently free tier
        )

    # stubs for generate etc.
    async def generate(self, *args, **kwargs):
        raise Exception("Groq API Key Invalid")
