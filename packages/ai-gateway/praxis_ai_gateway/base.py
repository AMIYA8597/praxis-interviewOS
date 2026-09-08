from typing import Protocol, AsyncIterator, Optional, Any
from pydantic import BaseModel

class LLMMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str

class LLMDelta(BaseModel):
    text: str
    is_final: bool

class LLMResponse(BaseModel):
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: float
    model: str
    provider: str

class ProviderCapabilities(BaseModel):
    streaming: bool
    structured_output: bool
    vision: bool
    embeddings: bool
    realtime_audio: bool
    max_context_tokens: int
    is_local: bool
    is_free_tier: bool

from praxis_ai_gateway.cancellation import CancellationToken

class LLMProvider(Protocol):
    name: str
    
    async def generate(self, messages: list[LLMMessage], cancellation_token: Optional[CancellationToken] = None, **kw) -> LLMResponse: ...
    async def stream(self, messages: list[LLMMessage], cancellation_token: Optional[CancellationToken] = None, **kw) -> AsyncIterator[LLMDelta]: ...
    async def structured(self, messages: list[LLMMessage], schema: type[BaseModel], cancellation_token: Optional[CancellationToken] = None, **kw) -> BaseModel: ...
    async def embed(self, texts: list[str], cancellation_token: Optional[CancellationToken] = None, **kw) -> list[list[float]]: ...
    def capabilities(self) -> ProviderCapabilities: ...
