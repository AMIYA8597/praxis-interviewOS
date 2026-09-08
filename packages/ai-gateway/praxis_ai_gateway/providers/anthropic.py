import os
import httpx
import json
import time
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError

class AnthropicProvider(LLMProvider):
    name = "anthropic"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.api_url = "https://api.anthropic.com/v1/messages"
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )

    def capabilities(self) -> ProviderCapabilities:
        if not self.api_key:
            return ProviderCapabilities(
                streaming=False, structured_output=False, vision=False, embeddings=False, 
                realtime_audio=False, max_context_tokens=0, is_local=False, is_free_tier=False
            )
            
        return ProviderCapabilities(
            streaming=True,
            structured_output=True, # Tool use / json
            vision=True,
            embeddings=False,
            realtime_audio=False,
            max_context_tokens=200000,
            is_local=False,
            is_free_tier=False
        )

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 401:
                raise ProviderAuthError("Anthropic auth error") from exc
            elif exc.response.status_code == 429:
                raise ProviderRateLimitError("Anthropic rate limited") from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("Anthropic server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("Anthropic timeout") from exc
        raise exc

    def _format_messages(self, messages: list[LLMMessage]):
        system = None
        msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                msgs.append({"role": m.role, "content": m.content})
        return system, msgs

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=None, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        system, msgs = self._format_messages(messages)
        start = time.perf_counter()
        
        payload = {
            "model": kw.get("model", "claude-3-5-sonnet-20240620"),
            "max_tokens": kw.get("max_tokens", 4096),
            "messages": msgs,
            "stream": False
        }
        if system:
            payload["system"] = system
            
        try:
            resp = await self._client.post(self.api_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return LLMResponse(
                text=data["content"][0]["text"],
                input_tokens=data.get("usage", {}).get("input_tokens"),
                output_tokens=data.get("usage", {}).get("output_tokens"),
                latency_ms=(time.perf_counter() - start) * 1000,
                model=payload["model"],
                provider=self.name
            )
        except Exception as e:
            self._handle_error(e)

    async def stream(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> AsyncIterator[LLMDelta]:
        system, msgs = self._format_messages(messages)
        payload = {
            "model": kw.get("model", "claude-3-5-sonnet-20240620"),
            "max_tokens": kw.get("max_tokens", 4096),
            "messages": msgs,
            "stream": True
        }
        if system:
            payload["system"] = system
            
        try:
            async with self._client.stream("POST", self.api_url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_cancelled():
                        break
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            continue
                        try:
                            data = json.loads(data_str)
                            if data["type"] == "content_block_delta" and data["delta"]["type"] == "text_delta":
                                yield LLMDelta(text=data["delta"]["text"], is_final=False)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            self._handle_error(e)

    async def structured(self, messages, schema, cancellation_token=None, **kw):
        return await with_cancellation(self._structured(messages, schema, cancellation_token=None, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        # Anthropic doesn't have an exact `response_format: json_object`, 
        # but we can enforce it via tools or prompting. We use basic prompt enforcement here.
        msgs = list(messages)
        msgs.append(LLMMessage(role="user", content="Return ONLY valid JSON matching the schema."))
        resp = await self.generate(msgs, cancellation_token, **kw)
        return schema.model_validate_json(resp.text)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=None, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not support embeddings")
