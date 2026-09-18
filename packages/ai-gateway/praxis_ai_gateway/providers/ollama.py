import httpx
import json
import time
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError

class OllamaProvider(LLMProvider):
    name = "ollama"
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.api_url = f"{self.base_url}/api/chat"
        self._client = httpx.AsyncClient(timeout=30.0)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=True, # Ollama supports LLaVA etc.
            embeddings=True,
            realtime_audio=False,
            max_context_tokens=8192,
            is_local=True,
            is_free_tier=True
        )

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 401:
                raise ProviderAuthError("Ollama auth error") from exc
            elif exc.response.status_code == 429:
                raise ProviderRateLimitError("Ollama rate limited") from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("Ollama server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("Ollama timeout") from exc
        raise exc

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=None, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": kw.get("model", "llama-3.1-8b-instruct"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {}
        }
        if "temperature" in kw:
            payload["options"]["temperature"] = kw["temperature"]
            
        try:
            resp = await self._client.post(self.api_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return LLMResponse(
                text=data["message"]["content"],
                input_tokens=data.get("prompt_eval_count"),
                output_tokens=data.get("eval_count"),
                latency_ms=(time.perf_counter() - start) * 1000,
                model=payload["model"],
                provider=self.name
            )
        except Exception as e:
            self._handle_error(e)

    async def stream(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> AsyncIterator[LLMDelta]:
        payload = {
            "model": kw.get("model", "llama-3.1-8b-instruct"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {}
        }
        try:
            async with self._client.stream("POST", self.api_url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_cancelled():
                        break
                    if not line:
                        continue
                    data = json.loads(line)
                    yield LLMDelta(
                        text=data["message"]["content"],
                        is_final=data.get("done", False)
                    )
        except Exception as e:
            self._handle_error(e)

    async def structured(self, messages, schema, cancellation_token=None, **kw):
        return await with_cancellation(self._structured(messages, schema, cancellation_token=None, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        # Ollama supports 'format: json'. 
        # For strict grammar, you'd pass a JSON schema, but format: json with a strong prompt is the native approach currently.
        payload = {
            "model": kw.get("model", "llama-3.1-8b-instruct"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "format": "json"
        }
        try:
            resp = await self._client.post(self.api_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Parse and repair step
            return schema.model_validate_json(data["message"]["content"])
        except Exception as e:
            self._handle_error(e)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=None, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        # This is technically not calling Ollama.
        # It's grouped under is_local=True because it runs on this machine with zero network cost.
        from praxis_ai_gateway.embeddings import embed_texts
        return await embed_texts(texts, normalize=kw.get("normalize", True), batch_size=kw.get("batch_size", 32))
