from typing import Protocol, AsyncIterator, List, Any, Dict, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    text: str
    usage: Dict[str, int]
    model_used: str

class LLMDelta(BaseModel):
    text: str

class ProviderCapabilities(BaseModel):
    streaming: bool
    structured_output: bool
    vision: bool
    embeddings: bool
    realtime_audio: bool
    max_context: int
    is_local: bool
    is_free_tier: bool

class LLMProvider(Protocol):
    async def generate(self, messages: List[Dict[str, Any]], **kw) -> LLMResponse: ...
    async def stream(self, messages: List[Dict[str, Any]], **kw) -> AsyncIterator[LLMDelta]: ...
    async def structured(self, messages: List[Dict[str, Any]], schema: type[BaseModel], **kw) -> BaseModel: ...
    async def embed(self, texts: List[str], **kw) -> List[List[float]]: ...
    def capabilities(self) -> ProviderCapabilities: ...
    def is_configured(self) -> bool: ...
