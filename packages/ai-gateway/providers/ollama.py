from typing import List, Dict, Any, AsyncIterator
from pydantic import BaseModel
import os
import aiohttp
import json

from packages.ai_gateway.base import LLMProvider, ProviderCapabilities, LLMResponse, LLMDelta

class OllamaProvider:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    def is_configured(self) -> bool:
        return True # Ollama is local, assumed always configured if requested

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=True, # Ollama supports format="json"
            vision=True if "vl" in self.model_id.lower() else False,
            embeddings=True,
            realtime_audio=False,
            max_context=8192,
            is_local=True,
            is_free_tier=True
        )

    async def generate(self, messages: List[Dict[str, Any]], **kw) -> LLMResponse:
        # Note: In a real implementation this would use aiohttp against the Ollama API
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model_id,
                "messages": messages,
                "stream": False
            }
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return LLMResponse(
                    text=data["message"]["content"],
                    usage={"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)},
                    model_used=self.model_id
                )

    async def stream(self, messages: List[Dict[str, Any]], **kw) -> AsyncIterator[LLMDelta]:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model_id,
                "messages": messages,
                "stream": True
            }
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.content:
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield LLMDelta(text=chunk["message"]["content"])

    async def structured(self, messages: List[Dict[str, Any]], schema: type[BaseModel], **kw) -> BaseModel:
        # Placeholder for structured JSON parsing
        return schema()

    async def embed(self, texts: List[str], **kw) -> List[List[float]]:
        return []
