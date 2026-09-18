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

def aggregate_session_data(session_id: str, db_stub: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 1: Aggregates ALREADY-COMPUTED data (metrics, scores, claims, jd).
    (Using a stubbed database mapping for this implementation phase).
    """
    turns = db_stub.get("turns", [])
    scores = db_stub.get("scores", [])
    metrics = db_stub.get("metrics", [])
    claims = db_stub.get("claims", [])
    jd_blueprint = db_stub.get("jd_blueprint", {"likely_topics": []})
    
    # Calculate simple averages safely
    avg_wpm = sum(m.get("wpm", 0) for m in metrics) / max(len(metrics), 1)
    avg_filler = sum(m.get("filler_rate", 0) for m in metrics) / max(len(metrics), 1)
    avg_score = sum(s.get("overall", 0) for s in scores) / max(len(scores), 1)
    
    # JD Coverage heuristic
    covered_topics = set()
    for t in turns:
        topic = t.get("topic")
        if topic:
            covered_topics.add(topic)
            
    likely_topics = set(jd_blueprint.get("likely_topics", []))
    missed_topics = list(likely_topics - covered_topics)
    
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

async def generate_debrief(session_id: str, db_stub: Dict[str, Any], gateway_router, routing_ctx) -> SessionDebrief:
    """
    Task 1 & 2: Generates the debrief using aggregated data and one structured call.
    """
    aggregated = aggregate_session_data(session_id, db_stub)
    
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

def trigger_debrief_generation(session_id: str, db_stub: Dict[str, Any], gateway_router, routing_ctx):
    """
    Task 3: Trigger Timing
    Fires off debrief generation as an asyncio background task to prevent blocking the state transition.
    """
    # In a real app, this could be an arq enqueue: await redis.enqueue_job("generate_debrief", session_id)
    # Here we use create_task for intra-process fire-and-forget.
    task = asyncio.create_task(generate_debrief(session_id, db_stub, gateway_router, routing_ctx))
    # We optionally attach a callback to save the result, but for this exercise we return the task for awaiting in tests
    return task
