import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.base import LLMProvider, ProviderCapabilities, LLMDelta

class FailingStreamProvider(LLMProvider):
    name = "failing_stream_provider"
    def capabilities(self): 
        return ProviderCapabilities(streaming=True, structured_output=False, vision=False, embeddings=False, realtime_audio=False, max_context_tokens=1000, is_local=True, is_free_tier=True)
    async def generate(self, *args, **kw): pass
    async def structured(self, *args, **kw): pass
    async def embed(self, *args, **kw): pass
    
    async def stream(self, *args, **kw) -> AsyncGenerator[LLMDelta, None]:
        yield LLMDelta(text="Prefix ", is_final=False)
        yield LLMDelta(text="chunks ", is_final=False)
        raise RuntimeError("Mid-stream connection drop!")

class BackupStreamProvider(LLMProvider):
    name = "backup_stream_provider"
    def capabilities(self): 
        return ProviderCapabilities(streaming=True, structured_output=True, vision=False, embeddings=False, realtime_audio=False, max_context_tokens=1000, is_local=True, is_free_tier=True)
    async def generate(self, *args, **kw): pass
    async def structured(self, *args, **kw): pass
    async def embed(self, *args, **kw): pass
    
    async def stream(self, *args, **kw) -> AsyncGenerator[LLMDelta, None]:
        yield LLMDelta(text="Backup ", is_final=False)
        yield LLMDelta(text="completes ", is_final=False)
        yield LLMDelta(text="it.", is_final=True)

@pytest.mark.asyncio
async def test_mid_stream_fallback():
    registry = MagicMock(spec=ModelRegistry)
    # The registry returns candidates: first Failing, then Backup
    registry.filter_candidates.return_value = [
        (FailingStreamProvider(), {"model": "failing"}),
        (BackupStreamProvider(), {"model": "backup"})
    ]
    
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.setex = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    
    router = GatewayRouter(registry=registry, providers={}, redis=redis, db=db)
    
    ctx = RoutingContext(user_id="user1")
    call = await router.route("test_task", ctx, "stream")
    
    assert call.provider_name == "router_stream"
    
    chunks = []
    async for chunk in call.result:
        chunks.append(chunk.text)
        
    # We should get Prefix chunks from failing, and then Backup chunks
    text = "".join(chunks)
    assert text == "Prefix chunks Backup completes it."
    
    # Verify fallback was logged
    assert db.execute.call_count > 0

class MalformedStructuredProvider(LLMProvider):
    name = "malformed_provider"
    def capabilities(self): 
        return ProviderCapabilities(streaming=False, structured_output=True, vision=False, embeddings=False, realtime_audio=False, max_context_tokens=1000, is_local=True, is_free_tier=True)
    async def generate(self, *args, **kw): pass
    async def stream(self, *args, **kw): pass
    async def embed(self, *args, **kw): pass
    
    async def structured(self, *args, **kw):
        # We simulate malformed JSON that fails parsing
        raise ValueError("Malformed JSON in response")

@pytest.mark.asyncio
async def test_structured_malformed_fallback():
    registry = MagicMock(spec=ModelRegistry)
    registry.filter_candidates.return_value = [
        (MalformedStructuredProvider(), {"model": "malformed"}),
        (BackupStreamProvider(), {"model": "backup"}) # fallback (we just reuse backup as it doesn't do structured well, but we can patch it)
    ]
    
    backup_provider = BackupStreamProvider()
    backup_provider.structured = AsyncMock(return_value="Success Object")
    registry.filter_candidates.return_value = [
        (MalformedStructuredProvider(), {"model": "malformed"}),
        (backup_provider, {"model": "backup"})
    ]
    
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.setex = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    
    router = GatewayRouter(registry=registry, providers={}, redis=redis, db=db)
    ctx = RoutingContext(user_id="user1")
    
    call = await router.route("test_task", ctx, "structured")
    
    # Confirm it fell back and got the success object
    assert call.provider_name == "backup_stream_provider"
    assert call.result == "Success Object"
