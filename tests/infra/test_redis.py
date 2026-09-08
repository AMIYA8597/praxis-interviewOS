import os
import pytest
import asyncio
from backend.core.redis_client import get_redis

pytestmark = pytest.mark.asyncio

async def test_redis_ttl_enforcement_and_expiration():
    client = get_redis()
    
    # 1. Confirm the "no TTL without explicit override" helper refuses a bare SET
    with pytest.raises(ValueError, match="Missing mandatory TTL for key"):
        await client.set("cache:test_key", "data")
        
    with pytest.raises(ValueError, match="Missing mandatory TTL for key"):
        await client.set("session:test_key", "data")

    # 2. Set a cache:* key with a very short TTL (1 second for faster tests, rather than 5)
    test_key = "cache:ttl_test"
    test_val = "temporary_data"
    
    await client.set(test_key, test_val, ex=1)
    
    # Confirm it exists
    val = await client.get(test_key)
    assert val == test_val, "Key should exist immediately after setting."
    
    # 3. Wait for it to expire (sleep 2 seconds to be safe)
    await asyncio.sleep(2)
    
    # Confirm it has expired
    expired_val = await client.get(test_key)
    assert expired_val is None, "Key should have expired and returned nil."
    
    # Cleanup (just in case the sleep was too short, though 2s > 1s)
    await client.delete(test_key)
