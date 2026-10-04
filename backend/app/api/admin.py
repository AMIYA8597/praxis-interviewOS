import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AuditLog, Candidate, Profile
from backend.app.dependencies import get_ai_gateway, get_db_session, require_admin
from backend.app.exceptions import NotFoundError
from backend.app.repositories.base import as_uuid, paginate
from backend.app.schemas.common import COMMON_ERROR_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"], responses=COMMON_ERROR_RESPONSES)


class BanRequest(BaseModel):
    user_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=500)


@router.get("/admin/users", response_model=dict)
async def list_users(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    page = await paginate(db, select(Candidate), Candidate, cursor=cursor, limit=limit)
    users = [
        {
            "id": str(c.id),
            "profile_id": str(c.profile_id),
            "full_name": c.full_name,
            "headline": c.headline,
            "created_at": c.created_at,
        }
        for c in page.items
    ]
    return {"users": users, "next_cursor": page.next_cursor}


@router.get("/admin/providers", response_model=dict)
async def get_admin_providers(admin: dict = Depends(require_admin), gateway=Depends(get_ai_gateway)):
    from backend.app.api.health import providers_check

    return await providers_check(gateway)


@router.get("/admin/audit-logs", response_model=dict)
async def get_audit_logs(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    page = await paginate(db, select(AuditLog), AuditLog, cursor=cursor, limit=limit)
    logs = [
        {
            "id": str(log.id),
            "profile_id": str(log.profile_id) if log.profile_id else None,
            "action": log.action,
            "resource": log.resource,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in page.items
    ]
    return {"logs": logs, "next_cursor": page.next_cursor}


@router.post("/admin/users/ban", response_model=dict)
async def ban_user(
    req: BanRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(update(Profile).where(Profile.id == req.user_id).values(is_banned=True))
    if not result.rowcount:
        raise NotFoundError("User")
    db.add(
        AuditLog(
            profile_id=as_uuid(admin.get("sub")),
            action="user_banned",
            resource=f"profiles/{req.user_id}",
            details={"reason": req.reason},
        )
    )
    await db.commit()
    logger.info("user_banned", extra={"target_user_id": str(req.user_id)})
    return {"status": "banned", "user_id": str(req.user_id), "reason": req.reason}
