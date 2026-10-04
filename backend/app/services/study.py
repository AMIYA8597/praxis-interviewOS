import base64
import binascii
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.queue import enqueue
from backend.app.core.storage import ObjectStorage
from backend.app.db.models import ScreenshotTask, SolverResult, StudyItem
from backend.app.exceptions import BadRequestError, PayloadTooLargeError, ServiceUnavailableError, NotFoundError
from backend.app.repositories import owned
from backend.app.repositories import study as repo
from backend.app.repositories.base import Page, as_uuid
from backend.app.schemas.study import (
    QueuedTaskResponse,
    ReviewItemResponse,
    StudyItemCreate,
)
from backend.app.services.sm2 import calculate_sm2

logger = logging.getLogger(__name__)


async def list_items(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    return await owned.list_owned(db, StudyItem, candidate_id, cursor=cursor, limit=limit)


async def create_item(db: AsyncSession, candidate_id: str, payload: StudyItemCreate) -> StudyItem:
    item = await owned.create_owned(db, StudyItem, candidate_id, {**payload.model_dump(), "source": "manual"})
    await db.commit()
    return item


async def due_items(db: AsyncSession, candidate_id: str, limit: int) -> List[StudyItem]:
    return await repo.list_due(db, candidate_id, limit)


async def review_item(db: AsyncSession, item_id, candidate_id: str, quality: int) -> ReviewItemResponse:
    item = await owned.get_owned(db, StudyItem, item_id, candidate_id)
    if item is None:
        raise NotFoundError("Study item")
    new_interval, new_reps, new_ef = calculate_sm2(
        quality,
        int(item.repetitions or 0),
        float(item.interval_days or 1),
        float(item.ease_factor or 2.5),
    )
    interval_days = max(1, int(round(new_interval)))
    next_review = datetime.now(timezone.utc) + timedelta(days=interval_days)
    item.ease_factor = new_ef
    item.interval_days = interval_days
    item.repetitions = new_reps
    item.next_review_at = next_review
    await repo.add_review(db, item.id, quality, interval_days, new_ef)
    await db.commit()
    return ReviewItemResponse(
        status="success",
        id=item.id,
        interval_days=interval_days,
        repetitions=new_reps,
        ease_factor=float(new_ef),
        next_review_at=next_review,
    )


async def queue_generation(arq_pool, candidate_id: str, topic: str, difficulty: str) -> QueuedTaskResponse:
    task_id = str(uuid.uuid4())
    queued = await enqueue(
        arq_pool, "generate_study_material_job", topic, difficulty, candidate_id, task_id, job_id=f"study:{task_id}"
    )
    if not queued:
        raise ServiceUnavailableError("Study generation queue unavailable")
    return QueuedTaskResponse(status="queued", task_id=task_id)


def _decode_image(image_base64: str, max_bytes: int) -> bytes:
    b64 = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
    if len(b64) > (max_bytes * 4) // 3 + 4:
        raise PayloadTooLargeError("Screenshot exceeds the size limit")
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise BadRequestError("image_base64 is not valid base64", code="invalid_image")
    if not data:
        raise BadRequestError("Empty image", code="invalid_image")
    return data


async def _owned_or_new_task(db, storage: ObjectStorage, candidate_id: str, task_ref: str, image: bytes) -> ScreenshotTask:
    task_uuid = as_uuid(task_ref)
    if task_uuid is not None:
        existing = await owned.get_owned(db, ScreenshotTask, task_uuid, candidate_id)
        if existing is not None:
            return existing
        # A UUID that exists for another candidate must not be reusable.
        other = (await db.execute(select(ScreenshotTask.id).where(ScreenshotTask.id == task_uuid))).first()
        if other is not None:
            raise NotFoundError("Screenshot task")
    task_id = task_uuid or uuid.uuid4()
    key = f"{candidate_id}/screenshots/{task_id}.img"
    try:
        await storage.put(key, image, "application/octet-stream")
    except Exception as e:
        logger.warning("screenshot_store_failed", extra={"error_type": type(e).__name__})
    task = ScreenshotTask(id=task_id, candidate_id=as_uuid(candidate_id), storage_path=key, status="processing")
    db.add(task)
    await db.flush()
    return task


async def solve_screenshot(db, storage, gateway, candidate: dict, image_base64: str, task_ref: str, max_bytes: int) -> dict:
    from praxis_ai_gateway.router import RoutingContext
    from praxis_ai_gateway.vision.ocr_pipeline import process_screenshot_hybrid
    from realtime_agent.app.study.solver import classify_screenshot, generate_hint_ladder

    image = _decode_image(image_base64, max_bytes)
    task = await _owned_or_new_task(db, storage, candidate["id"], task_ref, image)
    ctx = RoutingContext(user_id=candidate["user_id"], session_id=str(task.id))

    try:
        analysis = await process_screenshot_hybrid(image, gateway, ctx)
        screenshot_type = await classify_screenshot(analysis.extracted_text, gateway, ctx)
        hints = await generate_hint_ladder(analysis.extracted_text, screenshot_type, gateway, ctx)
    except Exception as e:
        logger.error("screenshot_solve_failed", extra={"error_type": type(e).__name__})
        task.status = "failed"
        await db.commit()
        raise ServiceUnavailableError("AI solver temporarily unavailable")

    stype = screenshot_type.value if hasattr(screenshot_type, "value") else str(screenshot_type)
    result = SolverResult(screenshot_task_id=task.id, screenshot_type=stype, hints=hints.model_dump())
    db.add(result)
    task.status = "solved"
    await db.commit()
    return {"id": str(result.id), "screenshot_task_id": str(task.id), "screenshot_type": stype, "hints": hints.model_dump()}


async def create_item_from_solve(db: AsyncSession, solver_result_id, candidate_id: str) -> StudyItem:
    rid = as_uuid(solver_result_id)
    if rid is None:
        raise NotFoundError("Solver result")
    stmt = (
        select(SolverResult)
        .join(ScreenshotTask, ScreenshotTask.id == SolverResult.screenshot_task_id)
        .where(SolverResult.id == rid, ScreenshotTask.candidate_id == as_uuid(candidate_id))
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    if result is None:
        raise NotFoundError("Solver result")
    hints = result.hints or {}
    concept = (hints.get("clarify") or "Screenshot problem").split(".")[0][:255]
    item = await owned.create_owned(
        db,
        StudyItem,
        candidate_id,
        {
            "topic": concept,
            "source": "screenshot_solve",
            "prompt": hints.get("approach") or concept,
            "reference_answer": hints.get("solution"),
            "solver_result_id": result.id,
        },
    )
    await db.commit()
    return item
