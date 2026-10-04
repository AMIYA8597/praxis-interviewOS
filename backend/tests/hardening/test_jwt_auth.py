"""
JWT verification through the real dependency chain (get_current_user ->
verify_jwt). Every token problem must produce 401 (never 500) with a
generic message, and JWKS key rotation must be picked up.
"""
import json
import time
import uuid

import fakeredis.aioredis
import httpx
import jwt
import pytest
import pytest_asyncio
import respx
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.app import auth as auth_module
from backend.app.dependencies import get_redis
from backend.app.main import app
from packages.config.settings import settings

SUPABASE_URL = "https://unit-test.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
HS_SECRET = "unit-test-hs256-secret-that-is-long-enough-123"


def _rsa_jwk(kid: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return key, public


def _claims(**overrides):
    now = int(time.time())
    claims = {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISSUER, "iat": now, "exp": now + 600,
              "email": "user@example.com", "role": "authenticated"}
    claims.update(overrides)
    return claims


@pytest.fixture(autouse=True)
def configured_auth(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", HS_SECRET)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS", False)
    monkeypatch.setattr(settings, "JWKS_REFRESH_COOLDOWN_S", 0)
    auth_module._memory_jwks.update(value=None, expires_at=0.0)
    yield
    auth_module._memory_jwks.update(value=None, expires_at=0.0)


@pytest_asyncio.fixture
async def client():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c
    app.dependency_overrides.clear()


def _hs(claims, secret=HS_SECRET):
    return jwt.encode(claims, secret, algorithm="HS256")


async def _me(client, token):
    return await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


@pytest.mark.asyncio
async def test_valid_hs256_token_is_accepted(client):
    claims = _claims()
    resp = await _me(client, _hs(claims))
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_id"] == claims["sub"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "token_factory",
    [
        lambda: "not-a-jwt",
        lambda: "a.b.c",
        lambda: _hs(_claims(), secret="wrong-secret-wrong-secret-wrong-secret"),
        lambda: _hs(_claims(aud="anon")),
        lambda: _hs(_claims(iss="https://evil.example.com/auth/v1")),
        lambda: _hs({k: v for k, v in _claims().items() if k != "sub"}),
        lambda: _hs({k: v for k, v in _claims().items() if k != "exp"}),
        lambda: jwt.encode(_claims(), key=None, algorithm="none"),
    ],
    ids=["garbage", "bad-segments", "bad-signature", "wrong-audience", "wrong-issuer", "no-sub", "no-exp", "alg-none"],
)
async def test_invalid_tokens_return_401(client, token_factory):
    resp = await _me(client, token_factory())
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["code"] == "unauthorized"
    assert resp.headers.get("www-authenticate") == "Bearer"
    # No secrets / internals in the error.
    assert HS_SECRET not in resp.text and "Traceback" not in resp.text


@pytest.mark.asyncio
async def test_expired_token_returns_401(client):
    now = int(time.time())
    resp = await _me(client, _hs(_claims(iat=now - 7200, exp=now - 3600)))
    assert resp.status_code == 401
    assert resp.json()["message"] == "Session expired"


@pytest.mark.asyncio
async def test_missing_authorization_header_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
@respx.mock
async def test_rs256_jwks_verification_and_key_rotation(client):
    old_key, old_jwk = _rsa_jwk("key-1")
    new_key, new_jwk = _rsa_jwk("key-2")
    route = respx.get(JWKS_URL).mock(return_value=httpx.Response(200, json={"keys": [old_jwk]}))

    token1 = jwt.encode(_claims(), old_key, algorithm="RS256", headers={"kid": "key-1"})
    assert (await _me(client, token1)).status_code == 200
    assert (await _me(client, token1)).status_code == 200
    assert route.call_count == 1, "JWKS must be served from cache on the second request"

    # Supabase rotates keys: a token with an unknown kid forces one refresh.
    route.mock(return_value=httpx.Response(200, json={"keys": [old_jwk, new_jwk]}))
    token2 = jwt.encode(_claims(), new_key, algorithm="RS256", headers={"kid": "key-2"})
    assert (await _me(client, token2)).status_code == 200
    assert route.call_count == 2

    # A kid that does not exist even after refresh is a 401, not a 500.
    rogue_key, _ = _rsa_jwk("rogue")
    token3 = jwt.encode(_claims(), rogue_key, algorithm="RS256", headers={"kid": "rogue"})
    assert (await _me(client, token3)).status_code == 401

    # Token signed by a different key but claiming a known kid -> 401.
    forged = jwt.encode(_claims(), rogue_key, algorithm="RS256", headers={"kid": "key-1"})
    assert (await _me(client, forged)).status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_jwks_outage_is_503_not_500(client):
    respx.get(JWKS_URL).mock(return_value=httpx.Response(500))
    key, _ = _rsa_jwk("key-1")
    token = jwt.encode(_claims(), key, algorithm="RS256", headers={"kid": "key-1"})
    resp = await _me(client, token)
    assert resp.status_code == 503
    assert resp.json()["code"] == "service_unavailable"


def test_env_example_has_no_values_swallowed_from_comments():
    """python-dotenv turns `KEY=   # comment` into the comment text; that must never happen
    (e.g. SUPABASE_JWT_SECRET would become a guessable 'secret')."""
    import os

    from packages.config.settings import Settings

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    cfg = Settings(_env_file=os.path.join(root, ".env.example"))
    leaked = {k: v for k, v in cfg.model_dump().items() if isinstance(v, str) and "#" in v}
    assert leaked == {}
    assert cfg.MAX_UPLOAD_BYTES == 10 * 1024 * 1024


def test_dev_bypass_is_impossible_in_production(monkeypatch):
    from packages.config.settings import Settings

    with pytest.raises(ValueError):
        Settings(APP_ENV="production", AUTH_DEV_BYPASS=True, SUPABASE_URL=SUPABASE_URL,
                 DATABASE_URL="postgresql://u:strong@db/praxis", CORS_ALLOW_ORIGINS="https://app.example.com")
    with pytest.raises(ValueError):
        Settings(APP_ENV="production", DATABASE_URL="postgresql://u:strong@db/praxis",
                 CORS_ALLOW_ORIGINS="https://app.example.com")  # no verifier configured
    with pytest.raises(ValueError):
        Settings(APP_ENV="production", SUPABASE_URL=SUPABASE_URL, DATABASE_URL="postgresql://u:strong@db/praxis",
                 CORS_ALLOW_ORIGINS="*")
    ok = Settings(APP_ENV="production", SUPABASE_URL=SUPABASE_URL, DATABASE_URL="postgresql://u:strong@db/praxis",
                  CORS_ALLOW_ORIGINS="https://app.example.com")
    assert ok.auth_dev_bypass_enabled is False and ok.api_docs_enabled is False
