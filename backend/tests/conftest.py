import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths  # noqa: E402,F401  (must run before app imports)

import pytest  # noqa: E402
from backend.app.main import app  # noqa: E402

from fastapi import Request, HTTPException
from backend.app.dependencies import get_current_user, require_admin, get_db_session, get_current_candidate

async def override_get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return {"sub": "test_user"}

async def override_get_current_candidate(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return {"id": "test_candidate_123", "profile_id": "test_user"}

async def override_require_admin(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or "admin" not in auth:
        raise HTTPException(status_code=403, detail="Not an admin")
    return {"sub": "admin_user"}

from unittest.mock import AsyncMock, MagicMock
async def override_get_db_session():
    mock_db = AsyncMock()
    # Mock execute to return something iteratable for tests like test_admin.py that do row._mapping
    mock_res = MagicMock()
    mock_res.fetchall.return_value = []
    
    mock_row = MagicMock()
    mock_row.total_sessions = 0
    mock_row.average_wpm = 0
    mock_row.average_filler_rate = 0
    mock_row.average_score = 0
    
    mock_res.fetchone.return_value = mock_row
    
    mock_db.execute.return_value = mock_res
    yield mock_db

async def override_get_redis():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b'test_candidate_123'
    yield mock_redis

from fastapi.testclient import TestClient
from backend.app.dependencies import get_redis

@pytest.fixture
def test_client():
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_candidate] = override_get_current_candidate
    app.dependency_overrides[require_admin] = override_require_admin
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = override_get_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_auth_token():
    return "test_token_user"

@pytest.fixture
def mock_auth_token_admin():
    return "test_token_admin"

@pytest.fixture
def auth_headers(mock_auth_token):
    return {"Authorization": f"Bearer {mock_auth_token}"}

@pytest.fixture
async def db_engine():
    """Async DB engine for integration tests that need a real database."""
    import os
    from sqlalchemy.ext.asyncio import create_async_engine
    raw_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis")
    if raw_url.startswith("postgresql://") and "asyncpg" not in raw_url:
        db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        db_url = raw_url
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            pass  # verify connectivity
    except Exception as e:
        pytest.skip(f"Database not accessible: {e}")
    try:
        yield engine
    finally:
        await engine.dispose()
