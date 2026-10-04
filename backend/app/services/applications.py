from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Application, Job
from backend.app.exceptions import NotFoundError
from backend.app.repositories import owned
from backend.app.repositories.base import Page
from backend.app.schemas.application import ApplicationCreate, ApplicationUpdate

_NOT_DELETED = (Application.deleted_at.is_(None),)


async def list_applications(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    return await owned.list_owned(db, Application, candidate_id, cursor=cursor, limit=limit, extra=_NOT_DELETED)


async def get_application(db: AsyncSession, app_id, candidate_id: str) -> Application:
    app = await owned.get_owned(db, Application, app_id, candidate_id, extra=_NOT_DELETED)
    if app is None:
        raise NotFoundError("Application")
    return app


async def create_application(db: AsyncSession, candidate_id: str, payload: ApplicationCreate) -> Application:
    if payload.job_id is not None and await owned.get_owned(db, Job, payload.job_id, candidate_id) is None:
        raise NotFoundError("Job")
    values = payload.model_dump()
    values["applied_at"] = datetime.now(timezone.utc) if values.get("status") == "applied" else None
    app = await owned.create_owned(db, Application, candidate_id, values)
    await db.commit()
    return app


async def update_application(db: AsyncSession, app_id, candidate_id: str, payload: ApplicationUpdate) -> Application:
    app = await owned.update_owned(
        db, Application, app_id, candidate_id, payload.model_dump(exclude_unset=True), extra=_NOT_DELETED
    )
    if app is None:
        raise NotFoundError("Application")
    await db.commit()
    return app


async def delete_application(db: AsyncSession, app_id, candidate_id: str) -> None:
    """Soft delete."""
    app = await owned.update_owned(
        db, Application, app_id, candidate_id, {"deleted_at": datetime.now(timezone.utc)}, extra=_NOT_DELETED
    )
    if app is None:
        raise NotFoundError("Application")
    await db.commit()
