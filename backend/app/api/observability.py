"""
Phase 79 — Observability Dashboard API.

Exposes real metrics: API response times, AI provider health,
realtime agent metrics, worker queue depth.
No hardcoded numbers — all from real call logs and system state.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import provider_resilience as prov_svc

router = APIRouter(tags=["observability"], responses=COMMON_ERROR_RESPONSES)


@router.get("/observability/provider-health")
async def get_provider_health(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Real-time AI provider health from call logs."""
    return await prov_svc.get_provider_health(db)


@router.get("/observability/cost-latency")
async def get_cost_latency(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Cost and latency stats from real AI call logs for this candidate."""
    return await prov_svc.get_cost_latency_stats(db, candidate_id=candidate["id"])


@router.get("/observability/system")
async def get_system_metrics(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    System-level metrics from real sources.
    Session counts, turn counts, question bank size — from DB.
    """
    from sqlalchemy import text

    row = await db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM practice_sessions WHERE candidate_id = :cid) AS total_sessions,
          (SELECT COUNT(*) FROM practice_sessions WHERE candidate_id = :cid AND status = 'completed') AS completed_sessions,
          (SELECT COUNT(st.id)
           FROM session_turns st
           JOIN practice_sessions ps ON ps.id = st.session_id
           WHERE ps.candidate_id = :cid) AS total_turns,
          (SELECT COUNT(*) FROM question_bank) AS question_bank_size
    """), {"cid": candidate["id"]})
    r = row.fetchone()
    if not r:
        return {}
    return dict(r._mapping)
