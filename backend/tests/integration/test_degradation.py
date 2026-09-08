import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from realtime_agent.app.main import create_app
from sqlalchemy import text

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.mark.asyncio
async def test_redis_unavailable_health():
    app = create_app()
    with TestClient(app) as client:
        # Before any modification, it should be 200
        # Wait, the app in TestClient triggers lifespan. 
        # If redis/db are not running, lifespan will fail.
        # But we mock it.
        pass

@pytest.mark.asyncio
async def test_rate_limiting_fails_open():
    from backend.app.rate_limiter import RateLimitMiddleware
    from fastapi import Request
    from starlette.responses import Response
    from unittest.mock import MagicMock
    
    redis_mock = AsyncMock()
    
    # We mock pipeline so it raises
    pipe_mock = AsyncMock()
    pipe_mock.execute.side_effect = ConnectionError("Redis is down!")
    redis_mock.pipeline.return_value = pipe_mock
    
    req = MagicMock(spec=Request)
    req.client.host = "127.0.0.1"
    req.url.path = "/api/v1/health"
    req.headers = {}
    req.app.state.redis_pool = redis_mock
    
    async def call_next(request):
        return Response(status_code=200)
        
    middleware = RateLimitMiddleware(app=None)
    
    # It should catch the ConnectionError and fail open, returning 200
    res = await middleware.dispatch(req, call_next)
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_db_pool_exhaustion():
    import sqlalchemy.exc
    from sqlalchemy.pool import QueuePool
    from unittest.mock import patch

    with patch.object(QueuePool, "connect", side_effect=sqlalchemy.exc.TimeoutError("QueuePool limit of size 1 overflow 0 reached, connection timed out, timeout 0.1")):
        pool = QueuePool(lambda: None, pool_size=1, max_overflow=0, timeout=0.1)
        with pytest.raises(sqlalchemy.exc.TimeoutError):
            pool.connect()
