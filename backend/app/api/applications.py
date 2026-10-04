import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.services import applications as service

router = APIRouter(tags=["applications"], responses=COMMON_ERROR_RESPONSES)


class ApplicationsPage(PaginatedResponse[ApplicationResponse]):
    # `applications` mirrors `items` for clients written against the old shape.
    applications: list[ApplicationResponse] = []


@router.get("/applications", response_model=ApplicationsPage)
async def list_applications(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_applications(db, candidate["id"], cursor, limit)
    return {"items": page.items, "applications": page.items, "next_cursor": page.next_cursor}


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    req: ApplicationCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.create_application(db, candidate["id"], req)


@router.get("/applications/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_application(db, app_id, candidate["id"])


@router.patch("/applications/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: uuid.UUID,
    req: ApplicationUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.update_application(db, app_id, candidate["id"], req)


@router.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    await service.delete_application(db, app_id, candidate["id"])
