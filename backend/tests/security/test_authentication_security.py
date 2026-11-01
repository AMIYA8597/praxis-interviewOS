"""
PRAXIS InterviewOS — Authentication Security Regression Suite
Verifies RS256 JWT validation, algorithm restriction, expiration, and fail-closed security.
"""
import json
import time
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

from backend.app import auth as auth_module
from backend.app.auth import AuthError, verify_jwt
from packages.config.settings import settings

SUPABASE_URL = "https://unit-test.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"


def _generate_rsa_keypair(kid: str = "key-1"):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return private_key, public_jwk


@pytest.fixture(autouse=True)
def configure_auth_env(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS", False)
    monkeypatch.setattr(settings, "JWT_AUDIENCE", "authenticated")
    auth_module._memory_jwks.update(value=None, expires_at=0.0)
    yield
    auth_module._memory_jwks.update(value=None, expires_at=0.0)


@pytest.mark.asyncio
async def test_valid_rs256_token_verifies_successfully(monkeypatch):
    priv_key, pub_jwk = _generate_rsa_keypair("k1")
    jwks = {"keys": [pub_jwk]}
    auth_module._memory_jwks.update(value=jwks, expires_at=time.monotonic() + 3600)

    now = int(time.time())
    sub = str(uuid.uuid4())
    claims = {
        "sub": sub,
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
    }
    token = jwt.encode(claims, priv_key, algorithm="RS256", headers={"kid": "k1"})

    payload = await verify_jwt(token, redis=None)
    assert payload["sub"] == sub
    assert payload["role"] == "authenticated"


@pytest.mark.asyncio
async def test_expired_token_is_rejected_with_401(monkeypatch):
    priv_key, pub_jwk = _generate_rsa_keypair("k1")
    jwks = {"keys": [pub_jwk]}
    auth_module._memory_jwks.update(value=jwks, expires_at=time.monotonic() + 3600)

    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now - 7200,
        "exp": now - 3600,  # Expired
    }
    token = jwt.encode(claims, priv_key, algorithm="RS256", headers={"kid": "k1"})

    with pytest.raises(AuthError) as exc_info:
        await verify_jwt(token, redis=None)
    assert exc_info.value.reason == "expired"


@pytest.mark.asyncio
async def test_none_algorithm_is_rejected():
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    # Unsigned token with alg: none
    token = jwt.encode(claims, key="", algorithm="none")

    with pytest.raises(AuthError) as exc_info:
        await verify_jwt(token, redis=None)
    assert exc_info.value.reason == "unsupported_alg"


@pytest.mark.asyncio
async def test_wrong_issuer_is_rejected():
    priv_key, pub_jwk = _generate_rsa_keypair("k1")
    jwks = {"keys": [pub_jwk]}
    auth_module._memory_jwks.update(value=jwks, expires_at=time.monotonic() + 3600)

    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": "https://malicious-attacker.com/auth/v1",  # Wrong issuer
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(claims, priv_key, algorithm="RS256", headers={"kid": "k1"})

    with pytest.raises(AuthError) as exc_info:
        await verify_jwt(token, redis=None)
    assert exc_info.value.reason == "InvalidIssuerError"


@pytest.mark.asyncio
async def test_missing_sub_is_rejected():
    priv_key, pub_jwk = _generate_rsa_keypair("k1")
    jwks = {"keys": [pub_jwk]}
    auth_module._memory_jwks.update(value=jwks, expires_at=time.monotonic() + 3600)

    now = int(time.time())
    claims = {
        # sub is omitted
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(claims, priv_key, algorithm="RS256", headers={"kid": "k1"})

    with pytest.raises(AuthError) as exc_info:
        await verify_jwt(token, redis=None)
    assert exc_info.value.reason in ("missing_sub", "MissingRequiredClaimError")


@pytest.mark.asyncio
async def test_malformed_token_syntax():
    with pytest.raises(AuthError) as exc_info:
        await verify_jwt("not.a.valid.jwt.token", redis=None)
    assert exc_info.value.reason == "malformed"
