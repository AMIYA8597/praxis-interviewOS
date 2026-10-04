import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import (
    get_ai_gateway,
    get_arq_pool,
    get_current_candidate,
    get_db_session,
    get_object_storage,
)
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.schemas.study import (
    GenerateMaterialRequest,
    QueuedTaskResponse,
    ReviewItemRequest,
    ReviewItemResponse,
    SolveScreenshotRequest,
    StudyItemCreate,
    StudyItemResponse,
)
from backend.app.services import study as service
from packages.config.settings import settings

router = APIRouter(tags=["study"], responses=COMMON_ERROR_RESPONSES)


@router.get("/study/items", response_model=PaginatedResponse[StudyItemResponse])
async def list_study_items(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_items(db, candidate["id"], cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor}


@router.get("/study/materials", response_model=dict, include_in_schema=False)
async def get_study_materials(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Legacy shape ({"materials": [...]}) kept for older clients; prefer GET /study/items."""
    page = await service.list_items(db, candidate["id"], cursor, limit)
    return {
        "materials": [StudyItemResponse.model_validate(i).model_dump(mode="json") for i in page.items],
        "next_cursor": page.next_cursor,
    }


@router.post("/study/items", response_model=StudyItemResponse, status_code=status.HTTP_201_CREATED)
async def create_study_item(
    payload: StudyItemCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.create_item(db, candidate["id"], payload)


@router.post("/study/generate", response_model=QueuedTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_study_material(
    req: GenerateMaterialRequest,
    candidate: dict = Depends(get_current_candidate),
    arq_pool=Depends(get_arq_pool),
):
    return await service.queue_generation(arq_pool, candidate["id"], req.topic, req.difficulty)


@router.post("/study/screenshots/solve", response_model=dict)
async def solve_screenshot_endpoint(
    req: SolveScreenshotRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    gateway=Depends(get_ai_gateway),
    storage=Depends(get_object_storage),
):
    return await service.solve_screenshot(
        db, storage, gateway, candidate, req.image_base64, req.screenshot_task_id, settings.MAX_UPLOAD_BYTES
    )


@router.post(
    "/study/items/from-solve/{solver_result_id}",
    response_model=StudyItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_item_from_solve(
    solver_result_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.create_item_from_solve(db, solver_result_id, candidate["id"])


@router.get("/study/items/due", response_model=dict)
async def get_due_items(
    limit: int = Query(10, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    items = await service.due_items(db, candidate["id"], limit)
    return {"items": [StudyItemResponse.model_validate(i).model_dump(mode="json") for i in items]}


@router.post("/study/items/{item_id}/review", response_model=ReviewItemResponse)
async def review_study_item(
    item_id: uuid.UUID,
    req: ReviewItemRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.review_item(db, item_id, candidate["id"], req.quality)
