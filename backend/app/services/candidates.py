import logging
from typing import Any, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Candidate
from backend.app.exceptions import BadRequestError, ConflictError, NotFoundError
from backend.app.repositories import candidates as repo
from backend.app.schemas.candidate import CandidateUpdate

logger = logging.getLogger(__name__)


async def get_profile(db: AsyncSession, candidate_id: str) -> Candidate:
    candidate = await repo.get(db, candidate_id)
    if candidate is None:
        raise NotFoundError("Candidate")
    return candidate


async def update_profile(db: AsyncSession, candidate_id: str, update: CandidateUpdate) -> Candidate:
    values = update.model_dump(exclude_unset=True)
    candidate = await repo.update_fields(db, candidate_id, values)
    if candidate is None:
        raise NotFoundError("Candidate")
    await db.commit()
    return candidate


async def upsert_profile(db: AsyncSession, user_id: str, update: CandidateUpdate) -> tuple[Candidate, bool]:
    """Create the caller's candidate row if missing (onboarding), else update it.

    Returns (candidate, created).
    """
    values: Dict[str, Any] = update.model_dump(exclude_unset=True)
    existing = await repo.get_for_profile(db, user_id)
    if existing is not None:
        candidate = await repo.update_fields(db, str(existing.id), values)
        await db.commit()
        return candidate, False

    if not values.get("full_name"):
        raise BadRequestError("full_name (or name) is required to create a profile", code="full_name_required")
    try:
        await repo.ensure_profile(db, user_id)
        candidate = await repo.create(db, user_id, values)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Either a concurrent create won, or profiles.id has no matching auth.users row.
        existing = await repo.get_for_profile(db, user_id)
        if existing is not None:
            return existing, False
        logger.warning("candidate_create_conflict")
        raise ConflictError("Unable to create candidate profile for this account")
    return candidate, True
