"""
Analytics API — original dashboard/reports endpoints + Phase 66-74 extensions.
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import analytics as service
from backend.app.services import improvement_engine as impr_svc
from backend.app.services import session_analytics as analytics_svc

router = APIRouter(tags=["analytics"], responses=COMMON_ERROR_RESPONSES)


class DashboardResponse(BaseModel):
    interviews_completed: int
    total_sessions: int
    average_pace_wpm: float
    filler_word_density: float
    average_score: float
    star_consistency: Optional[float] = None


class ReportsResponse(BaseModel):
    reports: List[Dict[str, Any]]


@router.get("/analytics/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.dashboard(db, candidate["id"])


@router.get("/analytics/reports", response_model=ReportsResponse)
async def get_reports(
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.reports(db, candidate["id"], limit)


# ── Phase 66: Daily Loop ──────────────────────────────────────────────────────

@router.get("/daily/recommendation")
async def get_daily_recommendation(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await analytics_svc.get_daily_recommendation(
        db, candidate["id"], str(job_id) if job_id else None
    )


# ── Phase 67: Session Comparison ─────────────────────────────────────────────

@router.post("/sessions/{session_id}/snapshot")
async def snapshot_session(
    session_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await analytics_svc.snapshot_session_performance(
        db, candidate["id"], str(session_id)
    )


@router.get("/sessions/compare")
async def compare_sessions(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await analytics_svc.compare_sessions(db, candidate["id"])


# ── Phase 68: Weakness Detection ─────────────────────────────────────────────

@router.post("/weaknesses/detect")
async def detect_weaknesses(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await analytics_svc.detect_and_persist_weaknesses(db, candidate["id"])


@router.get("/weaknesses")
async def get_weaknesses(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import text
    rows = await db.execute(text("""
        SELECT weakness_type, domain_code, description, severity,
               occurrence_count, first_observed_at, last_observed_at
        FROM candidate_weaknesses
        WHERE candidate_id = :cid AND resolved_at IS NULL
        ORDER BY severity DESC, occurrence_count DESC
    """), {"cid": candidate["id"]})
    return {"weaknesses": [dict(r._mapping) for r in rows.fetchall()]}


# ── Phase 71: Communication Coach ────────────────────────────────────────────

@router.get("/communication/recommendations")
async def get_communication_recommendations(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return {"recommendations": await impr_svc.get_communication_recommendations(db, candidate["id"])}


# ── Phase 72: Answer Replay ───────────────────────────────────────────────────

@router.get("/questions/{question_id}/attempts")
async def get_answer_history(
    question_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    history = await impr_svc.get_answer_history(db, candidate["id"], str(question_id))
    return {"attempts": history, "total": len(history)}


# ── Phase 73: Ideal Answer ────────────────────────────────────────────────────

class IdealAnswerRequest(BaseModel):
    question_text: str
    candidate_answer: str
    question_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None
    turn_id: Optional[uuid.UUID] = None
    turn_scores: Optional[dict] = None


@router.post("/improvement/ideal-answer")
async def generate_ideal_answer(
    body: IdealAnswerRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await impr_svc.generate_ideal_answer_feedback(
        db,
        candidate_id=candidate["id"],
        question_id=str(body.question_id) if body.question_id else None,
        session_id=str(body.session_id) if body.session_id else None,
        turn_id=str(body.turn_id) if body.turn_id else None,
        candidate_answer=body.candidate_answer,
        question_text=body.question_text,
        turn_score_data=body.turn_scores,
    )
