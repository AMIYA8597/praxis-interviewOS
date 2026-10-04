import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_arq_pool, get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.schemas.job import JobAcceptedResponse, JobCreate, JobDetailResponse, JobResponse
from backend.app.services import jobs as service

router = APIRouter(tags=["jobs"], responses=COMMON_ERROR_RESPONSES)


@router.post("/jobs", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    job_data: JobCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    arq_pool=Depends(get_arq_pool),
):
    return await service.create_job(db, arq_pool, candidate["id"], job_data)


@router.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_jobs(db, candidate["id"], cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor}


@router.get("/jobs/{id}", response_model=JobDetailResponse)
async def get_job(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_job(db, id, candidate["id"])


@router.delete("/jobs/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    await service.delete_job(db, id, candidate["id"])
