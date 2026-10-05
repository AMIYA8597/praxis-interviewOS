"""
Phase 71-74 — Communication Coach, Answer Replay, Ideal Answer, Memory Safety.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Phase 71: Communication Coach ───────────────────────────────────────────

def generate_communication_recommendations(
    avg_wpm: Optional[float],
    avg_filler_rate: Optional[float],
    avg_pause_count: Optional[float],
    avg_structure_score: Optional[float],
    top_fillers: Optional[list[str]],
) -> list[dict]:
    """
    Generate specific communication recommendations from real coaching metrics.
    Each recommendation includes the evidence that drove it.
    """
    recommendations = []

    if avg_wpm is not None:
        if avg_wpm < 100:
            recommendations.append({
                "area": "pace",
                "issue": f"Speaking pace is slow ({avg_wpm:.0f} WPM, target 120-160).",
                "recommendation": "Practice answering with a timer. Aim to cover the key points faster.",
                "evidence": f"avg_wpm={avg_wpm:.0f}",
            })
        elif avg_wpm > 180:
            recommendations.append({
                "area": "pace",
                "issue": f"Speaking pace is fast ({avg_wpm:.0f} WPM). Interviewers may miss key points.",
                "recommendation": "Pause intentionally between major points. Slow down on technical definitions.",
                "evidence": f"avg_wpm={avg_wpm:.0f}",
            })

    if avg_filler_rate is not None and avg_filler_rate > 0.05:
        filler_list = ", ".join(f"'{f}'" for f in (top_fillers or [])[:3])
        recommendations.append({
            "area": "filler_words",
            "issue": f"Filler rate is {avg_filler_rate:.1%} of words{' (top: ' + filler_list + ')' if filler_list else ''}.",
            "recommendation": (
                "Replace fillers with intentional pauses. When you feel an 'um' coming, "
                "stop and think silently instead."
            ),
            "evidence": f"avg_filler_rate={avg_filler_rate:.3f}",
        })

    if avg_pause_count is not None and avg_pause_count > 8:
        recommendations.append({
            "area": "pauses",
            "issue": f"High pause count per answer ({avg_pause_count:.1f} avg).",
            "recommendation": "Structure answers before speaking (STAR for behavioral, enumerate for technical). Fewer pauses mid-answer.",
            "evidence": f"avg_pause_count={avg_pause_count:.1f}",
        })

    if avg_structure_score is not None and avg_structure_score < 0.5:
        recommendations.append({
            "area": "structure",
            "issue": f"Answers lack clear structure (score={avg_structure_score:.2f}/1.0).",
            "recommendation": "Use signposting: 'There are three parts to this...' or 'First... second... finally...'",
            "evidence": f"avg_structure_score={avg_structure_score:.3f}",
        })

    if not recommendations:
        recommendations.append({
            "area": "general",
            "issue": None,
            "recommendation": "Communication metrics are within a good range. Focus on technical depth.",
            "evidence": "no_issues_detected",
        })

    return recommendations


async def get_communication_recommendations(
    db: AsyncSession, candidate_id: str
) -> list[dict]:
    row = await db.execute(text("""
        SELECT avg_wpm, avg_filler_rate, avg_pause_count, avg_structure_score, top_fillers
        FROM candidate_communication_profile WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    r = row.fetchone()
    if not r:
        return [{"area": "general", "issue": None,
                 "recommendation": "No communication data yet. Complete practice sessions with audio.",
                 "evidence": "no_data"}]
    return generate_communication_recommendations(
        float(r[0]) if r[0] else None,
        float(r[1]) if r[1] else None,
        float(r[2]) if r[2] else None,
        float(r[3]) if r[3] else None,
        list(r[4]) if r[4] else None,
    )


# ── Phase 72: Answer Replay ──────────────────────────────────────────────────

async def record_answer_attempt(
    db: AsyncSession,
    candidate_id: str,
    question_id: Optional[str],
    answer_text: str,
    overall_score: Optional[float],
    rationale: Optional[str],
) -> dict:
    """Record an answer attempt for replay comparison."""
    # Get current attempt number
    num_row = await db.execute(text("""
        SELECT COALESCE(MAX(attempt_number), 0)
        FROM answer_attempts
        WHERE candidate_id = :cid AND question_id = :qid
    """), {"cid": candidate_id, "qid": question_id})
    attempt_num = (num_row.scalar() or 0) + 1

    now = datetime.now(timezone.utc)
    row = await db.execute(text("""
        INSERT INTO answer_attempts
        (candidate_id, question_id, attempt_number, answer_text, overall_score, rationale, answered_at)
        VALUES (:cid, :qid, :num, :text, :score, :rationale, :now)
        RETURNING id
    """), {
        "cid": candidate_id, "qid": question_id, "num": attempt_num,
        "text": answer_text, "score": overall_score, "rationale": rationale, "now": now,
    })
    attempt_id = row.scalar()
    await db.commit()

    return {
        "attempt_id": str(attempt_id),
        "attempt_number": attempt_num,
        "overall_score": overall_score,
    }


async def get_answer_history(
    db: AsyncSession, candidate_id: str, question_id: str
) -> list[dict]:
    """Get all attempts for a question in chronological order."""
    rows = await db.execute(text("""
        SELECT attempt_number, answer_text, overall_score, rationale, answered_at
        FROM answer_attempts
        WHERE candidate_id = :cid AND question_id = :qid
        ORDER BY attempt_number ASC
    """), {"cid": candidate_id, "qid": question_id})
    return [dict(r._mapping) for r in rows.fetchall()]


# ── Phase 73: Ideal Answer / Improvement Mode ────────────────────────────────

async def generate_ideal_answer_feedback(
    db: AsyncSession,
    candidate_id: str,
    question_id: Optional[str],
    session_id: Optional[str],
    turn_id: Optional[str],
    candidate_answer: str,
    question_text: str,
    turn_score_data: Optional[dict],
    gateway_router=None,
    routing_ctx=None,
) -> dict:
    """
    Generate structured feedback: what was correct, what was missing,
    what would be stronger, + example answer structure.
    Uses LLM if available, falls back to score-driven heuristics.
    """
    now = datetime.now(timezone.utc)

    what_correct = None
    what_missing = None
    what_stronger = None
    example_answer = None

    if gateway_router is not None:
        from praxis_ai_gateway.prompt_builder import PromptBuilder
        from pydantic import BaseModel

        class ImprovementFeedback(BaseModel):
            what_was_correct: str
            what_was_missing: str
            what_would_be_stronger: str
            example_answer_structure: str

        builder = PromptBuilder()
        builder.add_system(
            "You are an expert interview coach. Analyze the candidate's answer and provide "
            "constructive improvement feedback. Be specific — cite what was said, not generic advice."
        )
        builder.add_trusted_context("question", question_text)
        builder.add_untrusted("candidate_answer", "realtime_stt", candidate_answer)
        if turn_score_data:
            builder.add_trusted_context("scores", json.dumps(turn_score_data))
        builder.add_output_schema(ImprovementFeedback)

        try:
            result = await gateway_router.route(
                "deep_reasoning", routing_ctx, "generate_structured",
                messages=[m.model_dump(exclude_none=True) for m in builder.build()],
                schema=ImprovementFeedback,
            )
            fb = result.result
            what_correct = fb.what_was_correct
            what_missing = fb.what_was_missing
            what_stronger = fb.what_would_be_stronger
            example_answer = fb.example_answer_structure
        except Exception as e:
            logger.warning("LLM ideal answer feedback failed: %s", e)

    # Score-driven fallback heuristics
    if what_correct is None and turn_score_data:
        scores = turn_score_data
        strengths = []
        if scores.get("relevance", 0) >= 0.7:
            strengths.append("answer was relevant to the question")
        if scores.get("structure", 0) >= 0.7:
            strengths.append("answer had clear structure")
        if scores.get("grounding", 0) >= 0.7:
            strengths.append("claims were grounded in context")
        what_correct = "; ".join(strengths) if strengths else "answer attempted the question"  # fallback

        gaps = []
        if scores.get("correctness", 1) < 0.6:
            gaps.append("technical accuracy needs improvement")
        if scores.get("specificity", 1) < 0.6:
            gaps.append("add more specific examples or metrics")
        if scores.get("structure", 1) < 0.6:
            gaps.append("use clearer answer structure (e.g. STAR for behavioral, enumerate for technical)")
        what_missing = "; ".join(gaps) if gaps else "answer could be more detailed"  # fallback

    await db.execute(text("""
        INSERT INTO ideal_answer_feedback
        (candidate_id, question_id, session_id, turn_id,
         what_was_correct, what_was_missing, what_was_stronger, example_answer, generated_at)
        VALUES (:cid, :qid, :sid, :tid, :correct, :missing, :stronger, :example, :now)
    """), {
        "cid": candidate_id, "qid": question_id, "sid": session_id, "tid": turn_id,
        "correct": what_correct, "missing": what_missing,
        "stronger": what_stronger, "example": example_answer, "now": now,
    })
    await db.commit()

    return {
        "what_was_correct": what_correct,
        "what_was_missing": what_missing,
        "what_would_be_stronger": what_stronger,
        "example_answer_structure": example_answer,
        "generated_at": now.isoformat(),
    }


# ── Phase 74: Memory Safety ──────────────────────────────────────────────────

class MemoryRetrievalConstraint:
    """
    Phase 74 — constrained retrieval. All memory lookups MUST pass through
    this constraint checker to ensure data is scoped to candidate_id.

    This prevents cross-candidate leakage in RAG and profile retrieval.
    """

    def __init__(self, candidate_id: str):
        self.candidate_id = candidate_id

    def validate_session(self, session_owner_candidate_id: str) -> bool:
        return session_owner_candidate_id == self.candidate_id

    def validate_turn(self, turn_owner_candidate_id: str) -> bool:
        return turn_owner_candidate_id == self.candidate_id

    def filter_query_params(self, params: dict) -> dict:
        """Ensure candidate_id is always present in query params."""
        params["candidate_id"] = self.candidate_id
        return params

    def safe_session_ids(self, session_ids: list[str], owned_ids: set[str]) -> list[str]:
        """Filter session_ids to only those owned by this candidate."""
        return [sid for sid in session_ids if sid in owned_ids]
