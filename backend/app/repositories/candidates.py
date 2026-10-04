from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AdminUser, Candidate, Profile
from backend.app.repositories.base import as_uuid


async def get_by_profile_id(db: AsyncSession, profile_id: str):
    """Return (id, is_banned) for the candidate owned by this auth user."""
    pid = as_uuid(profile_id)
    if pid is None:
        return None
    stmt = (
        select(Candidate.id, Profile.is_banned)
        .join(Profile, Profile.id == Candidate.profile_id, isouter=True)
        .where(Candidate.profile_id == pid)
        .order_by(Candidate.created_at.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).first()


async def get(db: AsyncSession, candidate_id: str) -> Optional[Candidate]:
    cid = as_uuid(candidate_id)
    if cid is None:
        return None
    return (await db.execute(select(Candidate).where(Candidate.id == cid))).scalar_one_or_none()


async def get_for_profile(db: AsyncSession, profile_id: str) -> Optional[Candidate]:
    pid = as_uuid(profile_id)
    if pid is None:
        return None
    stmt = select(Candidate).where(Candidate.profile_id == pid).order_by(Candidate.created_at.asc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def ensure_profile(db: AsyncSession, profile_id: str) -> None:
    stmt = pg_insert(Profile).values(id=as_uuid(profile_id)).on_conflict_do_nothing(index_elements=[Profile.id])
    await db.execute(stmt)


async def create(db: AsyncSession, profile_id: str, values: Dict[str, Any]) -> Candidate:
    candidate = Candidate(profile_id=as_uuid(profile_id), **values)
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def update_fields(db: AsyncSession, candidate_id: str, values: Dict[str, Any]) -> Optional[Candidate]:
    cid = as_uuid(candidate_id)
    if values:
        await db.execute(update(Candidate).where(Candidate.id == cid).values(**values))
    await db.flush()
    candidate = await get(db, candidate_id)
    if candidate is not None:
        await db.refresh(candidate)
    return candidate


async def is_admin(db: AsyncSession, profile_id: str) -> bool:
    pid = as_uuid(profile_id)
    if pid is None:
        return False
    row = (await db.execute(select(AdminUser.id).where(AdminUser.profile_id == pid))).first()
    return row is not None
