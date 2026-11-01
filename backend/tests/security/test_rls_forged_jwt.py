import pytest
import jwt
from unittest.mock import AsyncMock, MagicMock
from backend.app.dependencies import get_db_session
from backend.app.auth import AuthError

@pytest.mark.asyncio
async def test_forged_jwt_never_sets_rls_claims(monkeypatch):
    """
    Prove that dependencies.get_db_session derives request.jwt.claims ONLY from
    verify_jwt's verified result. A forged/tampered JWT is rejected and never
    sets request.jwt.claims.
    """
    # Create fake request with an unverified forged token
    forged_token = jwt.encode({"sub": "victim-user-id-1234"}, "wrong-secret", algorithm="HS256")
    
    request = MagicMock()
    request.headers = {"Authorization": f"Bearer {forged_token}"}
    request.app.state.redis_pool = None

    # Mock verify_jwt to simulate rejection of forged token
    mock_verify = AsyncMock(side_effect=AuthError("Signature verification failed"))
    monkeypatch.setattr("backend.app.dependencies.verify_jwt", mock_verify)

    executed_queries = []
    mock_session = AsyncMock()
    async def mock_execute(stmt, params=None):
        executed_queries.append((str(stmt), params))
        return MagicMock()
    mock_session.execute = mock_execute

    class DummyContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    request.app.state.db_session_factory = lambda: DummyContext()

    # Run get_db_session generator
    gen = get_db_session(request)
    session = await anext(gen)
    
    assert session is mock_session
    mock_verify.assert_awaited_once_with(forged_token, None)
    
    # Assert set_config was NEVER called with forged claims!
    set_config_calls = [q for q in executed_queries if "set_config" in q[0]]
    assert len(set_config_calls) == 0, f"VULNERABILITY: set_config was called with unverified claims: {set_config_calls}"

@pytest.mark.asyncio
async def test_verified_jwt_sets_rls_claims(monkeypatch):
    """
    Prove that when verify_jwt succeeds with a valid token, the verified claims
    are securely propagated to set_config('request.jwt.claims', ...).
    """
    valid_token = "valid.supabase.token"
    verified_claims = {"sub": "verified-user-456", "role": "authenticated"}
    
    request = MagicMock()
    request.headers = {"Authorization": f"Bearer {valid_token}"}
    request.app.state.redis_pool = None

    mock_verify = AsyncMock(return_value=verified_claims)
    monkeypatch.setattr("backend.app.dependencies.verify_jwt", mock_verify)

    executed_queries = []
    mock_session = AsyncMock()
    async def mock_execute(stmt, params=None):
        executed_queries.append((str(stmt), params))
        return MagicMock()
    mock_session.execute = mock_execute

    class DummyContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    request.app.state.db_session_factory = lambda: DummyContext()

    gen = get_db_session(request)
    session = await anext(gen)
    
    assert session is mock_session
    mock_verify.assert_awaited_once_with(valid_token, None)
    
    # Assert set_config was called with the exact verified claims
    set_config_calls = [q for q in executed_queries if "set_config" in q[0]]
    assert len(set_config_calls) == 1
    assert "verified-user-456" in set_config_calls[0][1]["claims"]
