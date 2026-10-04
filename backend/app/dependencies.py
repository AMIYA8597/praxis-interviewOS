"""
FastAPI dependencies: infrastructure handles and the authenticated principal.

`get_current_user`      -> verified JWT claims (401 on any token problem)
`get_current_candidate` -> {"id", "user_id", "profile_id"} for the caller's
                           candidate row (404 if onboarding not done yet)
"""
import logging
from typing import AsyncGenerator, Dict, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import AuthError, AuthProviderUnavailable, verify_jwt
from backend.app.core.context import bind
from backend.app.exceptions import (
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from packages.config.settings import settings

logger = logging.getLogger(__name__)

# auto_error=False so a missing header yields our 401 envelope instead of
# FastAPI's default 403.
security = HTTPBearer(auto_error=False)

CANDIDATE_CACHE_PREFIX = "cache:candidate_id:"


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a per-request async SQLAlchemy session; rolls back on error."""
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_redis(request: Request) -> Redis:
    """Provide the global Redis pool."""
    return request.app.state.redis_pool


async def get_arq_pool(request: Request):
    """ARQ pool, or None when the queue is unavailable (callers must handle)."""
    return getattr(request.app.state, "arq_pool", None)


async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict:
    """Verify the Supabase JWT and return its claims."""
    if token is None or not token.credentials:
        raise UnauthorizedError("Not authenticated")
    try:
        claims = await verify_jwt(token.credentials, redis)
    except AuthProviderUnavailable as e:
        raise ServiceUnavailableError(str(e))
    except AuthError as e:
        raise UnauthorizedError(str(e))
    user_id = str(claims.get("sub"))
    request.state.user_id = user_id
    bind(user_id=user_id)
    return claims


async def _lookup_candidate_id(user_id: str, db: AsyncSession) -> Optional[str]:
    from backend.app.repositories import candidates as candidates_repo

    row = await candidates_repo.get_by_profile_id(db, user_id)
    if row is None:
        return None
    if getattr(row, "is_banned", False):
        raise ForbiddenError("Account suspended", code="account_suspended")
    return str(row.id)


async def get_current_candidate(
    request: Request,
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Dict:
    """Resolve auth user (JWT `sub` == profiles.id) to candidates.id."""
    user_id = str(user.get("sub") or "")
    if not user_id:
        raise UnauthorizedError("Invalid session")

    cache_key = f"{CANDIDATE_CACHE_PREFIX}{user_id}"
    candidate_id: Optional[str] = None
    try:
        cached = await redis.get(cache_key)
        if cached:
            candidate_id = cached.decode() if isinstance(cached, bytes) else str(cached)
    except Exception as e:  # Redis down: fall through to the DB
        logger.warning("candidate_cache_read_failed", extra={"error_type": type(e).__name__})

    if not candidate_id:
        candidate_id = await _lookup_candidate_id(user_id, db)
        if not candidate_id:
            raise NotFoundError(
                "Candidate profile",
                message="Candidate profile not found. Complete onboarding first.",
                code="candidate_not_found",
            )
        try:
            await redis.set(cache_key, candidate_id, ex=settings.CANDIDATE_CACHE_TTL_S)
        except Exception as e:
            logger.warning("candidate_cache_write_failed", extra={"error_type": type(e).__name__})

    request.state.candidate_id = candidate_id
    bind(candidate_id=candidate_id)
    # profile_id kept as an alias of user_id for older callers.
    return {"id": candidate_id, "user_id": user_id, "profile_id": user_id}


async def invalidate_candidate_cache(redis: Redis, user_id: str) -> None:
    try:
        await redis.delete(f"{CANDIDATE_CACHE_PREFIX}{user_id}")
    except Exception:
        pass


async def require_admin(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Enforce admin access via the admin_users table (403 for non-admins)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise ForbiddenError("Invalid user token")
    from backend.app.repositories import candidates as candidates_repo

    try:
        is_admin = await candidates_repo.is_admin(db, str(user_id))
    except Exception:
        logger.exception("admin_check_failed")
        raise ServiceUnavailableError("Unable to verify admin status")
    if not is_admin:
        raise ForbiddenError("Admin access required")
    return current_user


async def get_ai_gateway(request: Request):
    """Provide the AI gateway router instance."""
    return request.app.state.ai_gateway


async def get_object_storage(request: Request):
    """Provide the ObjectStorage backend."""
    return request.app.state.object_storage
