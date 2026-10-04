from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import (
    get_current_candidate,
    get_current_user,
    get_db_session,
    get_redis,
    invalidate_candidate_cache,
)
from backend.app.schemas.candidate import CandidateResponse, CandidateUpdate
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import candidates as service

router = APIRouter(tags=["candidates"], responses=COMMON_ERROR_RESPONSES)


@router.get("/candidates/me", response_model=CandidateResponse)
async def get_me(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_profile(db, candidate["id"])


@router.patch("/candidates/me", response_model=CandidateResponse)
async def update_me(
    update_data: CandidateUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.update_profile(db, candidate["id"], update_data)


@router.put(
    "/candidates/me",
    response_model=CandidateResponse,
    responses={201: {"model": CandidateResponse}},
)
async def upsert_me(
    update_data: CandidateUpdate,
    response: Response,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    """Onboarding: create the caller's candidate profile, or update it if it exists."""
    candidate, created = await service.upsert_profile(db, str(user["sub"]), update_data)
    if created:
        response.status_code = status.HTTP_201_CREATED
        await invalidate_candidate_cache(redis, str(user["sub"]))
    return candidate
