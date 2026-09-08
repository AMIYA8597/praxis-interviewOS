import json
import logging
from typing import Optional
import httpx
import jwt
from redis.asyncio import Redis
from packages.config.settings import settings

logger = logging.getLogger(__name__)

async def get_jwks(redis: Redis) -> dict:
    if not settings.SUPABASE_URL:
        return {}
        
    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    cache_key = "cache:jwks"
    
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(jwks_url, timeout=5.0)
            resp.raise_for_status()
            jwks = resp.json()
            await redis.set(cache_key, json.dumps(jwks), ex=3600)
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise ValueError("Authentication provider unreachable")

async def verify_jwt(token: str, redis: Redis) -> dict:
    """Verify Supabase JWT and return the user payload."""
    if not settings.SUPABASE_URL:
        return {"sub": "00000000-0000-0000-0000-000000000000", "role": "authenticated"}

    jwks = await get_jwks(redis)
    
    try:
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
                
        if not rsa_key:
            raise ValueError("Public key not found in JWKS.")
            
        algorithm = rsa_key.get("alg", "RS256")
        
        payload = jwt.decode(
            token,
            key=jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(rsa_key)),
            algorithms=[algorithm],
            audience="authenticated",
            issuer=f"{settings.SUPABASE_URL}/auth/v1"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Invalid or expired session")
    except Exception as e:
        logger.warning(f"JWT processing error: {e}")
        raise ValueError("Invalid or expired session")
