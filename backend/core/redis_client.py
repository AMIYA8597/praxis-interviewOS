import os
from typing import Any, Optional
import redis.asyncio as redis

# Concrete connection pool limit as documented in Phase 1.8
MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", 10))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_pool_kwargs = {
    "max_connections": MAX_CONNECTIONS,
    "decode_responses": True,
}
if REDIS_URL.startswith("rediss://"):
    _ca_certs = os.environ.get("REDIS_SSL_CA_CERTS")
    if _ca_certs:
        _pool_kwargs["ssl_ca_certs"] = _ca_certs

_pool = redis.ConnectionPool.from_url(REDIS_URL, **_pool_kwargs)


class StrictRedisClient(redis.Redis):
    """
    A wrapper around the standard async Redis client that strictly enforces TTLs 
    for the cache:* and session:* namespaces.
    """
    async def set(
        self, 
        name: str, 
        value: Any, 
        ex: Optional[int] = None, 
        px: Optional[int] = None, 
        **kwargs
    ):
        # Enforce TTL on our ephemeral namespaces
        if name.startswith("cache:") or name.startswith("session:"):
            if ex is None and px is None and not kwargs.get("exat") and not kwargs.get("pxat"):
                raise ValueError(
                    f"StrictRedisClient: Missing mandatory TTL for key '{name}'. "
                    f"Keys in 'cache:*' and 'session:*' namespaces must explicitly expire."
                )
        
        return await super().set(name, value, ex=ex, px=px, **kwargs)


def get_redis() -> StrictRedisClient:
    return StrictRedisClient(connection_pool=_pool)
