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
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

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
            structured_output=True,
            vision=True,
            embeddings=True,
            realtime_audio=False,
            max_context_tokens=1048576, # 1M context
            is_local=False,
            is_free_tier=True
        )

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self._client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}", timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _handle_error(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            body_text = exc.response.text.lower() if exc.response is not None else ""
            if exc.response.status_code in [401, 403] or (exc.response.status_code == 400 and ("api key" in body_text or "api_key_invalid" in body_text)):
                raise ProviderAuthError("Gemini auth error") from exc
            elif exc.response.status_code == 429:
                retry_after = exc.response.headers.get("Retry-After")
                msg = f"Gemini rate limited (Retry-After: {retry_after})" if retry_after else "Gemini rate limited"
                raise ProviderRateLimitError(msg) from exc
            elif exc.response.status_code >= 500:
                raise ProviderServerError("Gemini server error") from exc
        elif isinstance(exc, httpx.TimeoutException):
            raise ProviderTimeoutError("Gemini timeout") from exc
        elif isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            raise ProviderServerError("Gemini connection failed") from exc
        raise exc

    def _format_messages(self, messages: list[LLMMessage]):
        # Simplified mapping for Gemini API (user/model)
        contents = []
        for m in messages:
            role = "user" if m.role in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents

    def _resolve_model(self, kw: dict) -> str:
        requested = kw.get("model")
        if requested in ("gemini-1.5-flash", "gemini-2.5-flash-lite"):
            requested = None
        return os.environ.get("GEMINI_MODEL") or requested or "gemini-3.1-flash-lite"

    async def generate(self, messages, cancellation_token=None, **kw):
        return await with_cancellation(self._generate(messages, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _generate(self, messages: list[LLMMessage], cancellation_token: Any = None, **kw) -> LLMResponse:
        model = self._resolve_model(kw)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        start = time.perf_counter()
        gen_config = {}
        if "temperature" in kw:
            gen_config["temperature"] = kw["temperature"]
        elif os.environ.get("LLM_TEMPERATURE"):
            try:
                gen_config["temperature"] = float(os.environ["LLM_TEMPERATURE"])
            except ValueError:
                pass
        if "max_tokens" in kw:
            gen_config["maxOutputTokens"] = kw["max_tokens"]
        elif os.environ.get("LLM_MAX_TOKENS"):
            try:
                gen_config["maxOutputTokens"] = int(os.environ["LLM_MAX_TOKENS"])
            except ValueError:
                pass

        payload = {"contents": self._format_messages(messages)}
        if gen_config:
            payload["generationConfig"] = gen_config
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
        model = self._resolve_model(kw)
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
        return await with_cancellation(self._structured(messages, schema, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Any = None, **kw) -> BaseModel:
        model = self._resolve_model(kw)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        formatted_messages = list(messages)
        schema_inst = f"\n\nOutput ONLY a JSON object that strictly conforms to this schema:\n{json.dumps(schema.model_json_schema())}"
        if formatted_messages:
            last_msg = formatted_messages[-1]
            formatted_messages[-1] = LLMMessage(role=last_msg.role, content=last_msg.content + schema_inst)
        else:
            formatted_messages = [LLMMessage(role="user", content=schema_inst)]

        # In Gemini v1beta, response_mime_type="application/json" is supported.
        payload = {
            "contents": self._format_messages(formatted_messages),
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            return schema.model_validate_json(text)
        except Exception as e:
            self._handle_error(e)

    async def embed(self, texts, cancellation_token=None, **kw):
        return await with_cancellation(self._embed(texts, cancellation_token=cancellation_token, **kw), cancellation_token)

    async def _embed(self, texts: list[str], cancellation_token: Any = None, **kw) -> list[list[float]]:
        model = kw.get("model", "gemini-embedding-001")
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
