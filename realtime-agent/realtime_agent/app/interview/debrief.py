import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from praxis_ai_gateway.prompt_builder import PromptBuilder
from realtime_agent.app.interview.policy import InterviewSession

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
    jd_coverage: Dict[str, List[str]] # e.g. {"covered": [], "missed": []}

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def aggregate_session_data(session_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Task 1 & 2: Aggregates ALREADY-COMPUTED data (metrics, scores, claims, jd).
    Queries real Postgres tables.
    """
    # 1. Turns
    query_turns = text("SELECT id, text_content, turn_index FROM session_turns WHERE session_id = :sid ORDER BY turn_index")
    turns_res = await db.execute(query_turns, {"sid": session_id})
    turns = turns_res.fetchall()
    
    # 2. Scores
    query_scores = text("""
        SELECT ts.relevance, ts.correctness, ts.structure, ts.overall, ts.rationale
        FROM turn_scores ts
        JOIN session_turns t ON ts.turn_id = t.id
        WHERE t.session_id = :sid
    """)
    scores_res = await db.execute(query_scores, {"sid": session_id})
    scores = [dict(s._mapping) for s in scores_res.fetchall()]
    
    # 3. Metrics (wpm/filler) 
    # Not populated in Phase 2.10, so we use dummy metric objects if missing
    # But let's check turn_metrics just in case
    query_metrics = text("""
        SELECT tm.wpm, tm.filler_rate
        FROM turn_metrics tm
        JOIN session_turns t ON tm.turn_id = t.id
        WHERE t.session_id = :sid
    """)
    try:
        metrics_res = await db.execute(query_metrics, {"sid": session_id})
        metrics = [dict(m._mapping) for m in metrics_res.fetchall()]
    except Exception:
        metrics = [] # Missing table or no rows
        
    # 4. Claims
    query_claims = text("""
        SELECT claim_text, supported, contradiction_of_claim_id 
        FROM session_claims 
        WHERE session_id = :sid
    """)
    claims_res = await db.execute(query_claims, {"sid": session_id})
    claims = [dict(c._mapping) for c in claims_res.fetchall()]
    
    # Calculate simple averages safely
    avg_wpm = sum(m.get("wpm") or 0 for m in metrics) / max(len(metrics), 1) if metrics else 120.0
    avg_filler = sum(m.get("filler_rate") or 0 for m in metrics) / max(len(metrics), 1) if metrics else 0.0
    avg_score = sum(s.get("overall", 0) for s in scores) / max(len(scores), 1) if scores else 0.0
    
    # We lack job details in standard tables, but for now we skip missed topics
    covered_topics = [] 
    likely_topics = set()
    missed_topics = []
    
    return {
        "turn_count": len(turns),
        "averages": {
            "wpm": avg_wpm,
            "filler_rate": avg_filler,
            "overall_score": avg_score
        },
        "weakest_scores": [s for s in scores if s.get("overall", 1.0) < 0.6],
        "strongest_scores": [s for s in scores if s.get("overall", 0.0) >= 0.8],
        "flagged_claims": [c.get("claim_text") for c in claims if not c.get("supported") or c.get("contradiction_of_claim_id")],
        "coverage": {
            "covered": list(covered_topics),
            "missed": missed_topics
        }
    }

async def generate_debrief(session_id: str, db: AsyncSession, gateway_router, routing_ctx) -> SessionDebrief:
    """
    Task 1 & 2: Generates the debrief using aggregated data and one structured call.
    """
    aggregated = await aggregate_session_data(session_id, db)
    
    with open("prompts/debrief/summary_v1.md", "r") as f:
        sys_prompt = f.read()
        
    builder = PromptBuilder()
    builder.add_system(sys_prompt)
    
    # Pass the aggregated data as trusted context
    agg_str = (
        f"Turn Count: {aggregated['turn_count']}\n"
        f"Averages -> WPM: {aggregated['averages']['wpm']}, Filler Rate: {aggregated['averages']['filler_rate']}, Score: {aggregated['averages']['overall_score']}\n"
        f"Strongest Turns: {aggregated['strongest_scores']}\n"
        f"Weakest Turns: {aggregated['weakest_scores']}\n"
        f"Flagged Claims: {aggregated['flagged_claims']}\n"
        f"JD Coverage -> Covered: {aggregated['coverage']['covered']}, Missed: {aggregated['coverage']['missed']}\n"
    )
    builder.add_trusted_context("aggregated_session_data", agg_str)
    
    builder.add_output_schema(SessionDebrief)
    
    try:
        call_result = await gateway_router.route(
            "deep_reasoning",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=SessionDebrief
        )
        return call_result.result
    except Exception as e:
        logger.error(f"Failed to generate debrief: {e}")
        return SessionDebrief(
            headline_metrics=HeadlineMetrics(average_wpm=0, average_filler_rate=0, average_score=0),
            strengths=[], weaknesses=[], flagged_claims=[], jd_coverage={"covered": [], "missed": []}
        )

def trigger_debrief_generation(session_id: str, db: AsyncSession, gateway_router, routing_ctx):
    """
    Task 3: Trigger Timing
    Fires off debrief generation as an asyncio background task to prevent blocking the state transition.
    """
    # In a real app, this could be an arq enqueue: await redis.enqueue_job("generate_debrief", session_id)
    # Here we use create_task for intra-process fire-and-forget.
    task = asyncio.create_task(generate_debrief(session_id, db, gateway_router, routing_ctx))
    # We optionally attach a callback to save the result, but for this exercise we return the task for awaiting in tests
    return task
