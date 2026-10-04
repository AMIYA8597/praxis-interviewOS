from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    PracticeSession,
    SessionDebrief,
    SessionTurn,
    TurnMetric,
    TurnScore,
)
from backend.app.repositories.base import as_uuid


async def list_turns(db: AsyncSession, session_id) -> List[SessionTurn]:
    stmt = (
        select(SessionTurn)
        .where(SessionTurn.session_id == as_uuid(session_id))
        .order_by(SessionTurn.turn_index.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_debrief(db: AsyncSession, session_id) -> Optional[SessionDebrief]:
    stmt = select(SessionDebrief).where(SessionDebrief.session_id == as_uuid(session_id))
    return (await db.execute(stmt)).scalar_one_or_none()


async def analytics_for_candidate(db: AsyncSession, candidate_id) -> dict:
    cid = as_uuid(candidate_id)
    total_sessions = (
        await db.execute(select(func.count(PracticeSession.id)).where(PracticeSession.candidate_id == cid))
    ).scalar() or 0
    completed_sessions = (
        await db.execute(
            select(func.count(PracticeSession.id)).where(
                PracticeSession.candidate_id == cid, PracticeSession.status == "completed"
            )
        )
    ).scalar() or 0
    metrics = (
        await db.execute(
            select(func.avg(TurnMetric.wpm), func.avg(TurnMetric.filler_rate))
            .join(SessionTurn, SessionTurn.id == TurnMetric.turn_id)
            .join(PracticeSession, PracticeSession.id == SessionTurn.session_id)
            .where(PracticeSession.candidate_id == cid, SessionTurn.speaker == "candidate")
        )
    ).first()
    scores = (
        await db.execute(
            select(func.avg(TurnScore.overall), func.avg(TurnScore.structure))
            .join(SessionTurn, SessionTurn.id == TurnScore.turn_id)
            .join(PracticeSession, PracticeSession.id == SessionTurn.session_id)
            .where(PracticeSession.candidate_id == cid)
        )
    ).first()
    return {
        "total_sessions": int(total_sessions),
        "completed_sessions": int(completed_sessions),
        "average_wpm": float(metrics[0]) if metrics and metrics[0] is not None else 0.0,
        "average_filler_rate": float(metrics[1]) if metrics and metrics[1] is not None else 0.0,
        "average_score": float(scores[0]) if scores and scores[0] is not None else 0.0,
        "average_structure": float(scores[1]) if scores and scores[1] is not None else None,
    }


async def session_score_history(db: AsyncSession, candidate_id, limit: int = 20) -> list:
    cid = as_uuid(candidate_id)
    stmt = (
        select(
            PracticeSession.id,
            PracticeSession.created_at,
            PracticeSession.interview_type,
            func.avg(TurnScore.overall),
            func.count(TurnScore.id),
        )
        .join(SessionTurn, SessionTurn.session_id == PracticeSession.id, isouter=True)
        .join(TurnScore, TurnScore.turn_id == SessionTurn.id, isouter=True)
        .where(PracticeSession.candidate_id == cid)
        .group_by(PracticeSession.id, PracticeSession.created_at, PracticeSession.interview_type)
        .order_by(PracticeSession.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "session_id": str(r[0]),
            "created_at": r[1],
            "interview_type": r[2],
            "average_score": float(r[3]) if r[3] is not None else None,
            "scored_turns": int(r[4] or 0),
        }
        for r in rows
    ]
