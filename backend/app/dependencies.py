import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
from jwt import PyJWKClient

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis
from packages.config.settings import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Stub gateway and storage until properly connected
class AIGatewayStub:
    def __init__(self):
        self.status = "not yet configured"
        
class ObjectStorageStub:
    pass

async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a per-request async SQLAlchemy session."""
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session

async def get_redis(request: Request) -> Redis:
    """Provide the global Redis pool."""
    return request.app.state.redis_pool

async def get_jwks(redis: Redis) -> dict:
    """Fetch JWKS from Supabase, heavily cached in Redis to prevent constant network trips."""
    if not settings.SUPABASE_URL:
        # For local dev fallback when bypass is needed
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
            # Cache for 1 hour
            await redis.set(cache_key, json.dumps(jwks), ex=3600)
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication provider unreachable"
            )

from backend.app.auth import verify_jwt

async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify Supabase JWT and return the user payload."""
    try:
        return await verify_jwt(token.credentials, redis)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def get_current_candidate(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
) -> Optional[dict]:
    """Map auth user to candidate row, caching in Redis."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
        
    cache_key = f"cache:candidate_id:{user_id}"
    cached_id = await redis.get(cache_key)
    
    if cached_id:
        return {"id": cached_id, "user_id": user_id}
        
    # Database lookup
    query = text("SELECT id FROM candidates WHERE profile_id = :user_id")
    result = await db.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if row:
        candidate_id = str(row[0])
        # Cache for 15 minutes
        await redis.set(cache_key, candidate_id, ex=900)
        return {"id": candidate_id, "user_id": user_id}
        
    return None

async def require_admin(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """Verify the user has admin privileges via DB query, not just JWT claim."""
    user_id = user.get("sub")
    
    # We query the profiles table to see if is_admin is true, or similar logic
    # In Stage 1 schema, candidates doesn't have is_admin, but we defined a function is_admin().
    # Actually, Stage 1 SQL `is_admin()` uses auth.uid() and profiles.
    query = text("SELECT is_admin FROM profiles WHERE id = :user_id")
    result = await db.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
        
    return user

async def get_ai_gateway(request: Request) -> AIGatewayStub:
    """Provide the AI gateway router instance."""
    return request.app.state.ai_gateway

async def get_object_storage(request: Request) -> ObjectStorageStub:
    """Provide the ObjectStorage protocol backend."""
    return request.app.state.object_storage

async def get_ai_gateway(request: Request) -> AIGatewayStub:
    """Provide the AI gateway router instance."""
    return request.app.state.ai_gateway

async def get_object_storage(request: Request) -> ObjectStorageStub:
    """Provide the ObjectStorage protocol backend."""
    return request.app.state.object_storage
