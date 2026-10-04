import logging
import uuid as _uuid
from typing import Dict, List
from pydantic import BaseModel

from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.base import LLMMessage

logger = logging.getLogger(__name__)

class HeadlineMetrics(BaseModel):
    average_wpm: float
    average_filler_rate: float
    average_score: float

class SessionDebrief(BaseModel):
    headline_metrics: HeadlineMetrics
    strengths: List[str]
    weaknesses: List[str]
    flagged_claims: List[str]
    jd_coverage: Dict[str, List[str]]

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models import TurnMetric, TurnScore, SessionTurn

async def generate_session_debrief(session_id: str, db: AsyncSession, gateway: GatewayRouter, user_id: str = "system") -> Dict:
    """
    Generates the Post-Session Debrief.
    Aggregates metrics and delegates the final summary to the reasoning alias
    using STRUCTURED output, bypassing token-heavy raw transcript reprocessing.
    
    NOTE: In a realtime session, realtime_agent/app/interview/debrief.py is primarily used. 
    This is an API-level fallback to regenerate a debrief from persisted DB tables if needed.
    """
    logger.info("debrief_generation_started", extra={"session_id": str(session_id)})
    
    # Query real Postgres tables
    stmt_metrics = select(TurnMetric).join(SessionTurn).where(SessionTurn.session_id == _uuid.UUID(str(session_id)))
    res_metrics = await db.execute(stmt_metrics)
    turn_metrics = res_metrics.scalars().all()
    
    stmt_scores = select(TurnScore).join(SessionTurn).where(SessionTurn.session_id == _uuid.UUID(str(session_id)))
    res_scores = await db.execute(stmt_scores)
    turn_scores = res_scores.scalars().all()
    
    # 1. Aggregate DSP Metrics
    avg_wpm = sum(float(m.wpm or 0) for m in turn_metrics) / len(turn_metrics) if turn_metrics else 0
    total_fillers = sum(int(m.filler_count or 0) for m in turn_metrics)
    avg_filler = total_fillers / len(turn_metrics) if turn_metrics else 0
    
    # 2. Aggregate Scores
    avg_relevance = sum(float(s.relevance or 0) for s in turn_scores) / len(turn_scores) if turn_scores else 0
    
    # 3. Identify Weakest Turn
    weakest_turn = min(turn_scores, key=lambda x: float(x.relevance or 0)) if turn_scores else None
    weakest_relevance = float(weakest_turn.relevance or 0) if weakest_turn else 'N/A'
    
    # 4. Invoke Reasoning Provider for natural language strengths/weaknesses
    prompt = f"""
    Based on the following aggregated session metrics, generate a strengths/weaknesses summary.
    Avg WPM: {avg_wpm}
    Avg Relevance: {avg_relevance}
    Total Fillers: {total_fillers}
    Weakest Turn Relevance: {weakest_relevance}
    """
    
    messages = [
        LLMMessage(role="user", content=prompt)
    ]
    
    try:
        resp = await gateway.route("deep_reasoning", RoutingContext(user_id=user_id, session_id=str(session_id)), "structured", messages=messages, schema=SessionDebrief)
        debrief: SessionDebrief = resp.result
        
        summary_parts = debrief.strengths + debrief.weaknesses
        return {
            "session_id": session_id,
            "summary": " ".join(summary_parts),
            "headline_metrics": debrief.headline_metrics.model_dump(),
            "strengths": debrief.strengths,
            "weaknesses": debrief.weaknesses,
            "flagged_claims": debrief.flagged_claims,
            "jd_coverage": debrief.jd_coverage,
        }
    except Exception as e:
        logger.error("debrief_generation_failed", extra={"session_id": str(session_id), "error_type": type(e).__name__})
        return {
            "session_id": session_id,
            "summary": "Failed to generate AI debrief summary.",
            "headline_metrics": {
                "average_wpm": round(avg_wpm),
                "average_filler_rate": total_fillers,
                "average_score": round(avg_relevance, 1)
            },
            "strengths": [],
            "weaknesses": ["Failed to generate AI debrief summary."],
            "flagged_claims": [],
            "jd_coverage": {},
        }


async def persist_session_debrief(db: AsyncSession, session_id: str, result: Dict) -> None:
    """Idempotent upsert of a generated debrief into session_debriefs."""
    import json
    from sqlalchemy import text

    await db.execute(
        text("""
            INSERT INTO session_debriefs (session_id, headline_metrics, strengths, weaknesses, flagged_claims,
                                          jd_coverage, generated_at)
            VALUES (CAST(:sid AS uuid), CAST(:hm AS jsonb), :strengths, :weaknesses, CAST(:fc AS jsonb),
                    CAST(:jd AS jsonb), now())
            ON CONFLICT (session_id) DO UPDATE SET
                headline_metrics = EXCLUDED.headline_metrics,
                strengths = EXCLUDED.strengths,
                weaknesses = EXCLUDED.weaknesses,
                flagged_claims = EXCLUDED.flagged_claims,
                jd_coverage = EXCLUDED.jd_coverage,
                generated_at = EXCLUDED.generated_at
        """),
        {
            "sid": str(session_id),
            "hm": json.dumps(result.get("headline_metrics") or {}),
            "strengths": list(result.get("strengths") or []),
            "weaknesses": list(result.get("weaknesses") or []),
            "fc": json.dumps(result.get("flagged_claims") or []),
            "jd": json.dumps(result.get("jd_coverage") or {}),
        },
    )
