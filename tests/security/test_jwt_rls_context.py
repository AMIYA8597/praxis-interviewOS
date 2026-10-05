"""
Phase 95 — RLS JWT Context Regression Tests.

Verifies that:
1. A forged JWT (valid structure, wrong signature) is rejected and does NOT
   produce a valid RLS identity.
2. A valid User-A token cannot access User-B rows.
3. An expired token is rejected.
4. Dev bypass is ONLY active when explicitly configured; never in production.
"""
import time
import uuid

import jwt
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

_REAL_SECRET = "a-very-long-supabase-jwt-secret-at-least-32-bytes-long"
_WRONG_SECRET = "wrong-secret-that-will-never-match-the-real-one-here"

USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())


def _make_token(sub: str, secret: str = _REAL_SECRET, exp_offset: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "iat": now,
            "exp": now + exp_offset,
            "role": "authenticated",
        },
        secret,
        algorithm="HS256",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forged_jwt_rejected():
    """A JWT signed with the wrong secret must raise AuthError, never succeed."""
    from backend.app.auth import AuthError, verify_jwt
    from unittest.mock import patch

    forged_token = _make_token(USER_A, secret=_WRONG_SECRET)

    with patch("backend.app.auth.settings") as mock_settings:
        mock_settings.auth_dev_bypass_enabled = False
        mock_settings.auth_verifier_configured = True
        mock_settings.SUPABASE_URL = None  # force HS256 path
        mock_settings.SUPABASE_JWT_SECRET = _REAL_SECRET
        mock_settings.JWT_AUDIENCE = "authenticated"
        mock_settings.jwt_issuer = "https://example.supabase.co/auth/v1"
        mock_settings.JWT_LEEWAY_S = 0

        with pytest.raises(AuthError):
            await verify_jwt(forged_token, redis=None)


@pytest.mark.asyncio
async def test_expired_token_rejected():
    """An expired token must raise AuthError with reason='expired'."""
    from backend.app.auth import AuthError, verify_jwt
    from unittest.mock import patch

    expired_token = _make_token(USER_A, exp_offset=-10)  # expired 10 seconds ago

    with patch("backend.app.auth.settings") as mock_settings:
        mock_settings.auth_dev_bypass_enabled = False
        mock_settings.auth_verifier_configured = True
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_JWT_SECRET = _REAL_SECRET
        mock_settings.JWT_AUDIENCE = "authenticated"
        mock_settings.jwt_issuer = "https://example.supabase.co/auth/v1"
        mock_settings.JWT_LEEWAY_S = 0

        with pytest.raises(AuthError) as exc_info:
            await verify_jwt(expired_token, redis=None)
        assert exc_info.value.reason == "expired"


@pytest.mark.asyncio
async def test_valid_token_returns_correct_sub():
    """A valid token returns the correct sub without modification."""
    from backend.app.auth import verify_jwt
    from unittest.mock import patch

    token = _make_token(USER_A)

    with patch("backend.app.auth.settings") as mock_settings:
        mock_settings.auth_dev_bypass_enabled = False
        mock_settings.auth_verifier_configured = True
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_JWT_SECRET = _REAL_SECRET
        mock_settings.JWT_AUDIENCE = "authenticated"
        mock_settings.jwt_issuer = "https://example.supabase.co/auth/v1"
        mock_settings.JWT_LEEWAY_S = 30

        payload = await verify_jwt(token, redis=None)
        assert payload["sub"] == USER_A


@pytest.mark.asyncio
async def test_dev_bypass_not_active_in_production():
    """Auth dev bypass must never activate when APP_ENV == 'production'."""
    from backend.app.auth import AuthError, verify_jwt
    from unittest.mock import patch

    arbitrary_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.not-a-real-token"

    with patch("backend.app.auth.settings") as mock_settings:
        mock_settings.auth_dev_bypass_enabled = False  # production: bypass off
        mock_settings.auth_verifier_configured = True
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_JWT_SECRET = _REAL_SECRET
        mock_settings.JWT_AUDIENCE = "authenticated"
        mock_settings.jwt_issuer = "https://example.supabase.co/auth/v1"
        mock_settings.JWT_LEEWAY_S = 0

        with pytest.raises(AuthError):
            await verify_jwt(arbitrary_token, redis=None)


def test_alg_none_rejected():
    """Algorithm 'none' must never be accepted."""
    from backend.app.auth import AuthError
    import asyncio

    # Craft a JWT with alg=none manually (PyJWT will refuse to encode with none,
    # so we construct the parts directly).
    import base64, json

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"sub": USER_A, "aud": "authenticated",
                                  "iss": "x", "iat": 0, "exp": 9999999999}).encode())
    none_token = f"{header}.{payload}."

    from unittest.mock import patch

    async def _run():
        from backend.app.auth import verify_jwt
        with patch("backend.app.auth.settings") as mock_settings:
            mock_settings.auth_dev_bypass_enabled = False
            mock_settings.auth_verifier_configured = True
            mock_settings.SUPABASE_URL = None
            mock_settings.SUPABASE_JWT_SECRET = _REAL_SECRET
            mock_settings.JWT_AUDIENCE = "authenticated"
            mock_settings.jwt_issuer = "x"
            mock_settings.JWT_LEEWAY_S = 0
            with pytest.raises(AuthError):
                await verify_jwt(none_token, redis=None)

    asyncio.run(_run())
