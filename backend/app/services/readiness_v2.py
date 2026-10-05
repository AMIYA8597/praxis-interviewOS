"""
Phase 58 — Interview Readiness 2.0.

Per-dimension scores with: confidence (sample_count-based), trend
(improving/stable/declining from session history), evidence (last 3 scores).

Not a single number — a multi-dimensional view grounded in evidence.
"""
import logging
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TrendType = Literal["improving", "stable", "declining", "insufficient_data"]


def _compute_trend(scores: list[float]) -> TrendType:
    if len(scores) < 3:
        return "insufficient_data"
    first_half = scores[: len(scores) // 2]
    second_half = scores[len(scores) // 2 :]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    delta = avg_second - avg_first
    if delta > 0.05:
        return "improving"
    if delta < -0.05:
        return "declining"
    return "stable"


def _confidence_label(sample_count: int) -> str:
    if sample_count >= 10:
        return "high"
    if sample_count >= 4:
        return "medium"
    if sample_count >= 1:
        return "low"
    return "no_data"


async def get_readiness_v2(db: AsyncSession, candidate_id: str) -> dict:
    """
    Return per-dimension readiness with confidence, trend, and evidence.
    Each dimension is computed from real session_turns scores.
    """
    # Pull all scored turns in chronological order for this candidate
    rows = await db.execute(text("""
        SELECT
            q.domain_code,
            ts.correctness,
            ts.grounding,
            ts.structure,
            ts.overall,
            st.started_at
        FROM session_turns st
        JOIN turn_scores ts ON ts.turn_id = st.id
        JOIN practice_sessions ps ON ps.id = st.session_id
        LEFT JOIN question_bank q ON q.id = st.question_id
        WHERE ps.candidate_id = :cid
          AND st.speaker = 'candidate'
          AND ts.overall IS NOT NULL
        ORDER BY st.started_at ASC
    """), {"cid": candidate_id})
    all_turns = rows.fetchall()

    if not all_turns:
        return {
            "dimensions": {},
            "overall": None,
            "message": "No scored sessions yet. Complete practice sessions to build readiness.",
        }

    # Group by domain
    domain_scores: dict[str, list[float]] = {}
    domain_ts: dict[str, list[str]] = {}
    all_overall: list[float] = []

    for row in all_turns:
        domain = row[0] or "general"
        overall = float(row[4]) if row[4] is not None else None
        if overall is None:
            continue
        domain_scores.setdefault(domain, []).append(overall)
        domain_ts.setdefault(domain, []).append(str(row[5]))
        all_overall.append(overall)

    dimensions = {}
    for domain, scores in domain_scores.items():
        trend = _compute_trend(scores)
        sample_count = len(scores)
        avg_score = sum(scores) / sample_count
        # Last 3 as evidence
        evidence = [round(s, 3) for s in scores[-3:]]
        timestamps = domain_ts[domain][-3:]

        dimensions[domain] = {
            "score": round(avg_score * 100, 1),
            "confidence": _confidence_label(sample_count),
            "sample_count": sample_count,
            "trend": trend,
            "evidence": [
                {"score": s, "at": t}
                for s, t in zip(evidence, timestamps)
            ],
        }

    overall_avg = sum(all_overall) / len(all_overall) if all_overall else None
    overall_trend = _compute_trend(all_overall)

    return {
        "dimensions": dimensions,
        "overall": {
            "score": round(overall_avg * 100, 1) if overall_avg else None,
            "confidence": _confidence_label(len(all_overall)),
            "trend": overall_trend,
            "sample_count": len(all_overall),
        },
    }
