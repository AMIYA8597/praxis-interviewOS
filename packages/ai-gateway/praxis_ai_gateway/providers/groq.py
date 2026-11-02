import os
import httpx
import json
import time
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel

from praxis_ai_gateway.base import LLMProvider, LLMMessage, LLMDelta, LLMResponse, ProviderCapabilities
from praxis_ai_gateway.cancellation_helper import with_cancellation
from praxis_ai_gateway.errors import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError

class GroqProvider(LLMProvider):
    name = "groq"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )

    def capabilities(self) -> ProviderCapabilities:
        if not self.api_key:
            return ProviderCapabilities(
                streaming=False,
                structured_output=False,
                vision=False,
                embeddings=False,
                realtime_audio=False,
                max_context_tokens=0,
                is_local=False,
                is_free_tier=False,
            )

        return ProviderCapabilities(
            streaming=True,
            structured_output=True, # Groq supports json_object response format
            vision=False,
            embeddings=False,
            realtime_audio=False,
            max_context_tokens=8192,
            is_local=False,
            is_free_tier=True
        )

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self._client.get("https://api.groq.com/openai/v1/models", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 401:
                raise ProviderAuthError("Groq auth error") from exc
            elif exc.response.status_code == 429:
                retry_after = exc.response.headers.get("Retry-After")
                msg = f"Groq rate limited (Retry-After: {retry_after})" if retry_after else "Groq rate limited"
                raise ProviderRateLimitError(msg) from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("Groq server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("Groq timeout") from exc
        elif isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            raise ProviderServerError("Groq connection failed") from exc
        raise exc

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": kw.get("model", "llama-3.1-8b-instant"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False
        }
        try:
            resp = await self._client.post(self.api_url, json=payload)
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
            "model": kw.get("model", "llama-3.1-8b-instant"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True
        }
        try:
            async with self._client.stream("POST", self.api_url, json=payload) as response:
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
                            yield LLMDelta(
                                text=delta["content"],
                                is_final=False
                            )
        except Exception as e:
            self._handle_error(e)

    async def structured(self, messages, schema, cancellation_token=None, **kw):
        return await with_cancellation(self._structured(messages, schema, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        has_json = any("json" in m["content"].lower() for m in formatted_messages)
        schema_json = json.dumps(schema.model_json_schema())
        if not has_json:
            instruction = f"\n\nPlease respond in valid JSON conforming to this schema:\n{schema_json}"
            if formatted_messages and formatted_messages[-1]["role"] == "user":
                formatted_messages[-1]["content"] += instruction
            else:
                formatted_messages.append({"role": "system", "content": f"Respond in valid JSON conforming to this schema:\n{schema_json}"})
        payload = {
            "model": kw.get("model", "llama-3.1-8b-instant"),
            "messages": formatted_messages,
            "response_format": {"type": "json_object"}
        }
        try:
            resp = await self._client.post(self.api_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            return schema.model_validate_json(raw_text)
        except Exception as e:
            self._handle_error(e)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        raise NotImplementedError("Groq does not support embeddings")
