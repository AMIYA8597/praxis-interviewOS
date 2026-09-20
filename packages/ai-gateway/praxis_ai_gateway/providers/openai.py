import os
import httpx
import json
import time
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError

class OpenAIProvider(LLMProvider):
    name = "openai"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1"
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )

    def capabilities(self) -> ProviderCapabilities:
        if not self.api_key:
            # Report unavailable essentially by claiming 0 tokens and no capabilities
            return ProviderCapabilities(
                streaming=False, structured_output=False, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=0, is_local=False, is_free_tier=False
            )
            
        return ProviderCapabilities(
            streaming=True,
            structured_output=True,
            vision=True,
            embeddings=True,
            realtime_audio=True,
            max_context_tokens=128000,
            is_local=False,
            is_free_tier=False
        )

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 401:
                raise ProviderAuthError("OpenAI auth error") from exc
            elif exc.response.status_code == 429:
                raise ProviderRateLimitError("OpenAI rate limited") from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("OpenAI server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("OpenAI timeout") from exc
        raise exc

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": kw.get("model", "gpt-4o-mini"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False
        }
        try:
            resp = await self._client.post(f"{self.api_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return LLMResponse(
                text=data["choices"][0]["message"]["content"],
                input_tokens=data.get("usage", {}).get("prompt_tokens"),
                output_tokens=data.get("usage", {}).get("completion_tokens"),
                latency_ms=(time.perf_counter() - start) * 1000,
                model=payload["model"],
                provider=self.name
            )
        except Exception as e:
            self._handle_error(e)

    async def stream(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> AsyncIterator[LLMDelta]:
        payload = {
            "model": kw.get("model", "gpt-4o-mini"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True
        }
        try:
            async with self._client.stream("POST", f"{self.api_url}/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_cancelled():
                        break
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield LLMDelta(text=delta["content"], is_final=False)
        except Exception as e:
            self._handle_error(e)

    async def structured(self, messages, schema, cancellation_token=None, **kw):
        return await with_cancellation(self._structured(messages, schema, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        payload = {
            "model": kw.get("model", "gpt-4o-mini"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "response_format": {"type": "json_object"}
        }
        try:
            resp = await self._client.post(f"{self.api_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return schema.model_validate_json(data["choices"][0]["message"]["content"])
        except Exception as e:
            self._handle_error(e)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        payload = {
            "model": kw.get("model", "text-embedding-3-small"),
            "input": texts
        }
        try:
            resp = await self._client.post(f"{self.api_url}/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [d["embedding"] for d in data["data"]]
        except Exception as e:
            self._handle_error(e)
