import logging
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.queue import enqueue
from backend.app.db.models import DeletionJob
from backend.app.dependencies import (
    get_arq_pool,
    get_current_candidate,
    get_current_user,
    get_db_session,
    get_redis,
    invalidate_candidate_cache,
)
from backend.app.exceptions import ServiceUnavailableError
from backend.app.repositories.base import as_uuid
from backend.app.schemas.common import COMMON_ERROR_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"], responses=COMMON_ERROR_RESPONSES)


class MeResponse(BaseModel):
    user_id: str
    email: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class DeletionQueuedResponse(BaseModel):
    status: str
    job_id: str


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(user: dict = Depends(get_current_user), redis: Redis = Depends(get_redis)):
    # Tokens are stateless (Supabase revokes refresh tokens client-side);
    # drop our server-side cache for the principal.
    await invalidate_candidate_cache(redis, str(user["sub"]))
    return {"message": "Logged out successfully"}


@router.get("/auth/me", response_model=MeResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return {"user_id": str(user.get("sub")), "email": user.get("email")}


@router.delete("/auth/account", response_model=DeletionQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def delete_account(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    arq_pool=Depends(get_arq_pool),
):
    """Queue an irreversible deletion of the caller's candidate data."""
    job = DeletionJob(
        profile_id=as_uuid(candidate["user_id"]),
        candidate_id=as_uuid(candidate["id"]),
        status="queued",
    )
    db.add(job)
    await db.commit()
    queued = await enqueue(
        arq_pool, "delete_candidate_account_job", str(job.id), candidate["id"], job_id=f"delete:{candidate['id']}"
    )
    if not queued:
        job.status = "failed"
        job.error_message = "Deletion queue unavailable"
        await db.commit()
        raise ServiceUnavailableError("Account deletion could not be scheduled; please retry")
    await invalidate_candidate_cache(redis, candidate["user_id"])
    logger.info("account_deletion_queued", extra={"deletion_job_id": str(job.id)})
    return {"status": "queued", "job_id": str(job.id)}
