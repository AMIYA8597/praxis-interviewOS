import os
import httpx
import json
import time
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError

class GeminiProvider(LLMProvider):
    name = "gemini"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=True,
            embeddings=True,
            realtime_audio=False,
            max_context_tokens=1048576, # 1M context
            is_local=False,
            is_free_tier=True
        )

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code in [401, 403]:
                raise ProviderAuthError("Gemini auth error") from exc
            elif exc.response.status_code == 429:
                raise ProviderRateLimitError("Gemini rate limited") from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("Gemini server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("Gemini timeout") from exc
        raise exc

    def _format_messages(self, messages: list[LLMMessage]):
        # Simplified mapping for Gemini API (user/model)
        contents = []
        for m in messages:
            role = "user" if m.role in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=None, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        model = kw.get("model", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        start = time.perf_counter()
        payload = {"contents": self._format_messages(messages)}
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return LLMResponse(
                text=text,
                input_tokens=usage.get("promptTokenCount"),
                output_tokens=usage.get("candidatesTokenCount"),
                latency_ms=(time.perf_counter() - start) * 1000,
                model=model,
                provider=self.name
            )
        except Exception as e:
            self._handle_error(e)

    async def stream(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> AsyncIterator[LLMDelta]:
        model = kw.get("model", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload = {"contents": self._format_messages(messages)}
        try:
            async with self._client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_cancelled():
                        break
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            yield LLMDelta(text=parts[0]["text"], is_final=False)
        except Exception as e:
            self._handle_error(e)

    async def structured(self, messages, schema, cancellation_token=None, **kw):
        return await with_cancellation(self._structured(messages, schema, cancellation_token=None, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        model = kw.get("model", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        # In Gemini v1beta, response_mime_type="application/json" is supported.
        payload = {
            "contents": self._format_messages(messages),
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return schema.model_validate_json(text)
        except Exception as e:
            self._handle_error(e)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=None, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        model = kw.get("model", "text-embedding-004")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={self.api_key}"
        
        requests = [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}} for t in texts]
        payload = {"requests": requests}
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [emb["values"] for emb in data["embeddings"]]
        except Exception as e:
            self._handle_error(e)
