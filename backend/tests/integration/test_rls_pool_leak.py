import asyncio
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

from backend.app.main import app
from packages.config.settings import settings

pytestmark = pytest.mark.asyncio

async def test_connection_pool_isolation():
    # Prove that transaction-local settings do not leak across pooled connections
    # We create a pool with exactly 1 connection to force reuse.
    
    engine = create_async_engine(
        settings.async_database_url, 
        pool_size=1, 
        max_overflow=0
    )
    
    # We don't have access to the actual test tokens easily here since it requires full JWT verification logic,
    # so we'll mock the dependency `get_current_user` to simulate A, B and anonymous,
    # and then rely on the app's db session yielding.
    
    # But wait, we want to prove `set_config` is cleared. 
    # Let's just run raw SQL queries on the engine simulating the dependency logic.
    
    from sqlalchemy import text
    async with engine.connect() as conn:
        # User A's request
        async with conn.begin():
            await conn.execute(
                text("SELECT set_config('request.jwt.claims', '{\"sub\": \"user_a\"}', true)")
            )
            val = await conn.scalar(text("SELECT current_setting('request.jwt.claims', true)"))
            assert val == '{"sub": "user_a"}'
        
        # Now transaction ended. Let's see if the connection still has user_a.
        # User B's request
        async with conn.begin():
            # Before setting it, what is it?
            val = await conn.scalar(text("SELECT current_setting('request.jwt.claims', true)"))
            assert val == '' or val is None
            
            await conn.execute(
                text("SELECT set_config('request.jwt.claims', '{\"sub\": \"user_b\"}', true)")
            )
            val2 = await conn.scalar(text("SELECT current_setting('request.jwt.claims', true)"))
            assert val2 == '{"sub": "user_b"}'
            
        # Anonymous request
        async with conn.begin():
            val = await conn.scalar(text("SELECT current_setting('request.jwt.claims', true)"))
            assert val == '' or val is None

    await engine.dispose()
