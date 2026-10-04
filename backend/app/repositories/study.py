from datetime import datetime, timezone
from typing import List

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import StudyItem, StudyReview
from backend.app.repositories.base import as_uuid


async def list_due(db: AsyncSession, candidate_id, limit: int = 10) -> List[StudyItem]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(StudyItem)
        .where(
            StudyItem.candidate_id == as_uuid(candidate_id),
            or_(StudyItem.next_review_at.is_(None), StudyItem.next_review_at <= now),
        )
        .order_by(StudyItem.next_review_at.asc().nulls_first(), StudyItem.created_at.asc())
        .limit(max(1, min(limit, 100)))
    )
    return list((await db.execute(stmt)).scalars().all())


async def add_review(db: AsyncSession, item_id, quality: int, new_interval_days: int, new_ease_factor: float) -> StudyReview:
    review = StudyReview(
        item_id=as_uuid(item_id),
        quality=quality,
        new_interval_days=new_interval_days,
        new_ease_factor=new_ease_factor,
    )
    db.add(review)
    await db.flush()
    return review
