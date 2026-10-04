import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_arq_pool, get_current_candidate, get_db_session, get_object_storage
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, ErrorResponse, PaginatedResponse
from backend.app.schemas.resume import (
    ResumeFactResponse,
    ResumeFactUpdate,
    ResumeResponse,
    ResumeStatusResponse,
    ResumeUploadResponse,
)
from backend.app.services import resumes as service
from packages.config.settings import settings

router = APIRouter(tags=["resumes"], responses=COMMON_ERROR_RESPONSES)


async def _upload(file, candidate, db, storage, arq_pool) -> ResumeUploadResponse:
    return await service.upload_resume(
        db, storage, arq_pool, candidate_id=candidate["id"], file=file, max_bytes=settings.MAX_UPLOAD_BYTES
    )


_UPLOAD_RESPONSES = {413: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.post(
    "/resumes",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_UPLOAD_RESPONSES,
)
async def upload_resume(
    file: UploadFile = File(...),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    storage=Depends(get_object_storage),
    arq_pool=Depends(get_arq_pool),
):
    """Accept a PDF/DOCX/TXT resume (<= MAX_UPLOAD_BYTES); parsing happens asynchronously."""
    return await _upload(file, candidate, db, storage, arq_pool)


@router.post(
    "/resumes/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_UPLOAD_RESPONSES,
    include_in_schema=False,
)
async def upload_resume_legacy(
    file: UploadFile = File(...),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    storage=Depends(get_object_storage),
    arq_pool=Depends(get_arq_pool),
):
    """Alias used by the web onboarding page."""
    return await _upload(file, candidate, db, storage, arq_pool)


@router.get("/resumes", response_model=PaginatedResponse[ResumeResponse])
async def list_resumes(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_resumes(db, candidate["id"], cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor}


@router.get("/resumes/{id}", response_model=ResumeStatusResponse)
async def get_resume_status(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_status(db, id, candidate["id"])


@router.get("/resumes/{id}/facts", response_model=List[ResumeFactResponse])
async def get_resume_facts(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.list_facts(db, id, candidate["id"])


@router.post("/resumes/{id}/facts/{fact_id}/confirm", response_model=ResumeFactResponse)
async def confirm_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.confirm_fact(db, id, fact_id, candidate["id"])


@router.post("/resumes/{id}/facts/{fact_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    await service.reject_fact(db, id, fact_id, candidate["id"])


@router.patch("/resumes/{id}/facts/{fact_id}", response_model=ResumeFactResponse)
async def update_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    update_data: ResumeFactUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.update_fact(db, id, fact_id, candidate["id"], update_data.content)
