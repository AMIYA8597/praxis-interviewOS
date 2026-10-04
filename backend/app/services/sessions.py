import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.context import bind
from backend.app.core.queue import enqueue
from backend.app.db.models import Job, PracticeSession
from backend.app.exceptions import ConflictError, NotFoundError
from backend.app.repositories import owned
from backend.app.repositories import sessions as repo
from backend.app.repositories.base import Page
from backend.app.schemas.session import (
    SessionCreate,
    SessionDebriefResponse,
    SessionEndResponse,
    SessionTurnResponse,
)

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"completed", "abandoned", "failed"}


async def create_session(db: AsyncSession, candidate_id: str, payload: SessionCreate) -> PracticeSession:
    if payload.job_id is not None:
        # Never let a session reference someone else's job.
        if await owned.get_owned(db, Job, payload.job_id, candidate_id) is None:
            raise NotFoundError("Job")
    session = await owned.create_owned(
        db,
        PracticeSession,
        candidate_id,
        {
            "job_id": payload.job_id,
            "focus_area": payload.focus_area,
            "mode": payload.mode,
            "interview_type": payload.interview_type,
            "difficulty": payload.difficulty,
            "language": payload.language,
            "status": "pending",
        },
    )
    await db.commit()
    bind(session_id=str(session.id))
    logger.info("session_created", extra={"session_id": str(session.id)})
    return session


async def list_sessions(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    return await owned.list_owned(db, PracticeSession, candidate_id, cursor=cursor, limit=limit)


async def get_session(db: AsyncSession, session_id, candidate_id: str) -> PracticeSession:
    session = await owned.get_owned(db, PracticeSession, session_id, candidate_id)
    if session is None:
        raise NotFoundError("Session")
    bind(session_id=str(session.id))
    return session


async def list_turns(db: AsyncSession, session_id, candidate_id: str) -> List[SessionTurnResponse]:
    session = await get_session(db, session_id, candidate_id)
    return [SessionTurnResponse.model_validate(t) for t in await repo.list_turns(db, session.id)]


async def get_debrief(db: AsyncSession, session_id, candidate_id: str) -> SessionDebriefResponse:
    session = await get_session(db, session_id, candidate_id)
    debrief = await repo.get_debrief(db, session.id)
    if debrief is None:
        return SessionDebriefResponse(status="pending", session_id=session.id)
    return SessionDebriefResponse(
        status="ready",
        id=debrief.id,
        session_id=session.id,
        headline_metrics=debrief.headline_metrics,
        strengths=list(debrief.strengths or []),
        weaknesses=list(debrief.weaknesses or []),
        flagged_claims=debrief.flagged_claims,
        jd_coverage=debrief.jd_coverage,
        generated_at=debrief.generated_at,
    )


async def end_session(db: AsyncSession, arq_pool, session_id, candidate_id: str) -> SessionEndResponse:
    """Mark a session completed and schedule debrief generation (idempotent)."""
    session = await get_session(db, session_id, candidate_id)
    if session.status in ("abandoned", "failed"):
        raise ConflictError(f"Session already {session.status}")
    if session.status != "completed":
        now = datetime.now(timezone.utc)
        session.status = "completed"
        session.ended_at = now
        if session.started_at:
            session.duration_s = int((now - session.started_at).total_seconds())
        await db.commit()

    if await repo.get_debrief(db, session.id) is not None:
        return SessionEndResponse(id=session.id, status=session.status, debrief_status="ready")
    queued = await enqueue(
        arq_pool, "generate_session_debrief_job", str(session.id), job_id=f"debrief:{session.id}"
    )
    return SessionEndResponse(id=session.id, status=session.status, debrief_status="queued" if queued else "unavailable")
