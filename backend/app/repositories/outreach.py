from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Application, OutreachDraft
from backend.app.repositories.base import Page, as_uuid, paginate


async def list_drafts(db: AsyncSession, candidate_id, *, cursor: Optional[str], limit: int) -> Page:
    # Ownership flows through the parent application.
    stmt = (
        select(OutreachDraft)
        .join(Application, Application.id == OutreachDraft.application_id)
        .where(Application.candidate_id == as_uuid(candidate_id), Application.deleted_at.is_(None))
    )
    return await paginate(db, stmt, OutreachDraft, cursor=cursor, limit=limit)


async def create_draft(db: AsyncSession, application_id, subject: Optional[str], body: str, recipient_name: Optional[str]) -> OutreachDraft:
    draft = OutreachDraft(
        application_id=as_uuid(application_id), subject=subject, body=body, recipient_name=recipient_name
    )
    db.add(draft)
    await db.flush()
    await db.refresh(draft)
    return draft
