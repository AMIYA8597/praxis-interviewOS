"""
Supabase JWT verification.

* Asymmetric tokens (RS256/ES256/EdDSA) are verified against the project's
  JWKS endpoint. The key set is cached in Redis (and in-process) for
  `JWKS_CACHE_TTL_S` seconds. When a token carries an unknown `kid` (key
  rotation) the cache is bypassed and the JWKS is re-fetched, rate-limited
  by `JWKS_REFRESH_COOLDOWN_S` so garbage tokens cannot hammer Supabase.
* Legacy HS256 tokens are verified with SUPABASE_JWT_SECRET when configured.
* `exp`, `iat`, `sub`, `aud` and `iss` are mandatory and validated.
* Error messages are deliberately generic; the precise reason is logged
  server-side (never the token itself).
"""
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
import jwt
from redis.asyncio import Redis

from packages.config.settings import settings

logger = logging.getLogger(__name__)

JWKS_CACHE_KEY = "cache:jwks"
JWKS_REFRESH_LOCK_KEY = "cache:jwks:refresh_lock"

ASYMMETRIC_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "PS256", "EdDSA"}
SYMMETRIC_ALGORITHMS = {"HS256"}

# In-process fallback cache, used when Redis is unavailable.
_memory_jwks: Dict[str, Any] = {"value": None, "expires_at": 0.0}
_last_forced_refresh = 0.0


class AuthError(ValueError):
    """Token is missing, malformed, expired or otherwise invalid (-> 401).

    Subclasses ValueError for backwards compatibility with callers that
    caught ValueError from verify_jwt.
    """

    def __init__(self, message: str = "Invalid or expired session", reason: str = "invalid_token"):
        super().__init__(message)
        self.reason = reason


class AuthProviderUnavailable(AuthError):
    """The JWKS endpoint could not be reached (-> 503, not the client's fault)."""

    def __init__(self, message: str = "Authentication provider unreachable"):
        super().__init__(message, reason="jwks_unavailable")


def _jwks_url() -> str:
    return f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"


async def _fetch_jwks() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_jwks_url())
            resp.raise_for_status()
            jwks = resp.json()
    except Exception as e:
        # Do not include the response body; it may be large or sensitive.
        logger.error("jwks_fetch_failed", extra={"error_type": type(e).__name__})
        raise AuthProviderUnavailable() from e
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        logger.error("jwks_malformed")
        raise AuthProviderUnavailable()
    return jwks


async def _cache_get(redis: Optional[Redis]) -> Optional[Dict[str, Any]]:
    if redis is not None:
        try:
            cached = await redis.get(JWKS_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("jwks_cache_read_failed", extra={"error_type": type(e).__name__})
    if _memory_jwks["value"] and _memory_jwks["expires_at"] > time.monotonic():
        return _memory_jwks["value"]
    return None


async def _cache_set(redis: Optional[Redis], jwks: Dict[str, Any]) -> None:
    _memory_jwks["value"] = jwks
    _memory_jwks["expires_at"] = time.monotonic() + settings.JWKS_CACHE_TTL_S
    if redis is not None:
        try:
            await redis.set(JWKS_CACHE_KEY, json.dumps(jwks), ex=settings.JWKS_CACHE_TTL_S)
        except Exception as e:
            logger.warning("jwks_cache_write_failed", extra={"error_type": type(e).__name__})


async def _may_force_refresh(redis: Optional[Redis]) -> bool:
    """Allow at most one forced JWKS refresh per cooldown window (cluster-wide when Redis is up)."""
    global _last_forced_refresh
    cooldown = settings.JWKS_REFRESH_COOLDOWN_S
    if cooldown <= 0:
        return True
    if redis is not None:
        try:
            return bool(await redis.set(JWKS_REFRESH_LOCK_KEY, "1", ex=cooldown, nx=True))
        except Exception:
            pass
    now = time.monotonic()
    if now - _last_forced_refresh >= cooldown:
        _last_forced_refresh = now
        return True
    return False


async def get_jwks(redis: Optional[Redis], force_refresh: bool = False) -> Dict[str, Any]:
    """Return the Supabase JWKS, served from cache unless `force_refresh`."""
    if not settings.SUPABASE_URL:
        return {"keys": []}
    if not force_refresh:
        cached = await _cache_get(redis)
        if cached:
            return cached
    jwks = await _fetch_jwks()
    await _cache_set(redis, jwks)
    return jwks


def _find_key(jwks: Dict[str, Any], kid: Optional[str]) -> Optional[Dict[str, Any]]:
    for key in jwks.get("keys", []):
        if kid and key.get("kid") == kid:
            return key
    return None


def _decode(token: str, key: Any, algorithm: str) -> Dict[str, Any]:
    options = {"require": ["exp", "iat", "sub"]}
    issuer = settings.jwt_issuer
    return jwt.decode(
        token,
        key=key,
        algorithms=[algorithm],
        audience=settings.JWT_AUDIENCE,
        issuer=issuer,
        leeway=settings.JWT_LEEWAY_S,
        options=options,
    )


def _dev_bypass_payload() -> Dict[str, Any]:
    return {
        "sub": settings.AUTH_DEV_USER_ID,
        "role": "authenticated",
        "aud": settings.JWT_AUDIENCE,
        "dev_bypass": True,
    }


async def verify_jwt(token: str, redis: Optional[Redis]) -> Dict[str, Any]:
    """Verify a Supabase access token and return its claims.

    Raises AuthError (401) for any client-side problem and
    AuthProviderUnavailable (503) when the JWKS cannot be fetched.
    """
    if settings.auth_dev_bypass_enabled:
        return _dev_bypass_payload()

    if not settings.auth_verifier_configured:
        # Fail closed: no verifier and bypass not allowed.
        logger.error("auth_not_configured")
        raise AuthProviderUnavailable("Authentication is not configured")

    if not token or not isinstance(token, str) or token.count(".") != 2:
        raise AuthError(reason="malformed")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise AuthError(reason="malformed_header")

    alg = header.get("alg")
    kid = header.get("kid")

    try:
        if alg in SYMMETRIC_ALGORITHMS:
            if not settings.SUPABASE_JWT_SECRET:
                raise AuthError(reason="hs256_not_configured")
            payload = _decode(token, settings.SUPABASE_JWT_SECRET, alg)
        elif alg in ASYMMETRIC_ALGORITHMS:
            if not settings.SUPABASE_URL:
                raise AuthError(reason="jwks_not_configured")
            jwks = await get_jwks(redis)
            jwk = _find_key(jwks, kid)
            if jwk is None and await _may_force_refresh(redis):
                # Possible key rotation: refetch once, bypassing the cache.
                jwks = await get_jwks(redis, force_refresh=True)
                jwk = _find_key(jwks, kid)
            if jwk is None:
                raise AuthError(reason="unknown_kid")
            key_alg = jwk.get("alg")
            if key_alg and key_alg != alg:
                raise AuthError(reason="alg_mismatch")
            public_key = jwt.PyJWK(jwk, algorithm=alg).key
            payload = _decode(token, public_key, alg)
        else:
            # Includes "none" and anything unexpected.
            raise AuthError(reason="unsupported_alg")
    except jwt.ExpiredSignatureError:
        logger.info("jwt_rejected", extra={"reason": "expired"})
        raise AuthError("Session expired", reason="expired")
    except AuthError as e:
        if not isinstance(e, AuthProviderUnavailable):
            logger.info("jwt_rejected", extra={"reason": e.reason})
        raise
    except jwt.PyJWTError as e:
        logger.info("jwt_rejected", extra={"reason": type(e).__name__})
        raise AuthError(reason=type(e).__name__)
    except Exception as e:
        logger.warning("jwt_processing_error", extra={"error_type": type(e).__name__})
        raise AuthError(reason="processing_error")

    if not payload.get("sub"):
        raise AuthError(reason="missing_sub")
    return payload
