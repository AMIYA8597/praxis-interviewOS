import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from backend.app.services import projects as service

router = APIRouter(tags=["projects"], responses=COMMON_ERROR_RESPONSES)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.create_project(db, candidate["id"], project_data)


@router.get("/projects", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_projects(db, candidate["id"], cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor}


@router.get("/projects/{id}", response_model=ProjectResponse)
async def get_project(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_project(db, id, candidate["id"])


@router.patch("/projects/{id}", response_model=ProjectResponse)
async def update_project(
    id: uuid.UUID,
    update_data: ProjectUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.update_project(db, id, candidate["id"], update_data)


@router.delete("/projects/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    await service.delete_project(db, id, candidate["id"])
