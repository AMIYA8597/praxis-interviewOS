import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.schemas.question_bank import PreparationPlanResponse, ReadinessResponse
from backend.app.services import readiness as svc

router = APIRouter(tags=["readiness"], responses=COMMON_ERROR_RESPONSES)


@router.get("/readiness", response_model=ReadinessResponse)
async def get_readiness(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    result = await svc.compute_readiness(db, uuid.UUID(candidate["id"]), job_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed sessions found — complete at least one practice session first.",
        )
    return result


@router.post("/readiness/plan", response_model=PreparationPlanResponse, status_code=status.HTTP_200_OK)
async def generate_plan(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    result = await svc.generate_preparation_plan(db, uuid.UUID(candidate["id"]), job_id)
    return result


@router.get("/readiness/plan", response_model=PreparationPlanResponse)
async def get_plan(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import text
    params = {"candidate_id": str(candidate["id"])}
    q = "SELECT * FROM preparation_plans WHERE candidate_id = :candidate_id"
    if job_id:
        q += " AND job_id = :job_id"
        params["job_id"] = str(job_id)
    else:
        q += " AND job_id IS NULL"
    q += " LIMIT 1"
    row = (await db.execute(text(q), params)).mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preparation plan found. POST /readiness/plan to generate one.",
        )
    return dict(row)
