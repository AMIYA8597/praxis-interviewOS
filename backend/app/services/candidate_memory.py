"""
Phase 55 — Candidate Memory & Personalization.

Facts (measurable from session data) are kept strictly separated from
Inferences (interpretations of facts). Facts are updated deterministically
after every session. Inferences are generated only when facts support them
and are explicitly tagged as inferences.

SM-2 spaced repetition parameters are updated from real session scores.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# SM-2 ease factor bounds
_SM2_MIN_EASE = 1.3
_SM2_MAX_EASE = 3.5

# Mastery thresholds — based on factual session counts and correctness
_MASTERY_RULES = {
    # (min_sessions, min_correctness_avg) → mastery_status
    "mastered_for_now": (5, 0.85),
    "proficient":       (3, 0.70),
    "developing":       (2, 0.50),
    "learning":         (1, 0.0),
}


def _compute_mastery(sessions: int, avg_correctness: Optional[float]) -> str:
    if sessions == 0 or avg_correctness is None:
        return "unknown"
    for status, (min_s, min_c) in _MASTERY_RULES.items():
        if sessions >= min_s and avg_correctness >= min_c:
            return status
    return "learning"


def _sm2_update(
    interval: int, ease: float, repetitions: int, score_0_to_5: float
) -> tuple[int, float, int, datetime]:
    """
    SM-2 algorithm update.
    score_0_to_5: converted from correctness float [0,1] × 5
    Returns: (new_interval_days, new_ease, new_repetitions, next_review_at)
    """
    q = score_0_to_5
    new_ease = max(_SM2_MIN_EASE, min(_SM2_MAX_EASE, ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))

    if q < 3.0:  # failed recall
        new_reps = 0
        new_interval = 1
    else:
        new_reps = repetitions + 1
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease)

    next_review = datetime.now(timezone.utc) + timedelta(days=new_interval)
    return new_interval, new_ease, new_reps, next_review


async def update_topic_facts_from_session(
    db: AsyncSession,
    candidate_id: str,
    session_id: str,
) -> None:
    """
    After a session completes: aggregate real turn scores by domain and upsert
    candidate_topic_facts. Then generate inferences from the updated facts.
    """
    # Pull scored turns for this session joined to domain via question_bank
    rows = await db.execute(text("""
        SELECT
            q.domain_code,
            ts.correctness,
            ts.grounding,
            ts.structure
        FROM session_turns st
        JOIN turn_scores ts ON ts.turn_id = st.id
        LEFT JOIN question_bank q ON q.id = st.question_id
        WHERE st.session_id = :session_id
          AND st.speaker = 'candidate'
          AND ts.correctness IS NOT NULL
    """), {"session_id": session_id})
    turn_rows = rows.fetchall()

    if not turn_rows:
        logger.info("update_topic_facts: no scored turns for session %s", session_id)
        return

    # Aggregate per domain
    domain_data: dict[str, dict] = {}
    for row in turn_rows:
        domain = row[0] or "general"
        corr = float(row[1]) if row[1] is not None else 0.5
        grnd = float(row[2]) if row[2] is not None else 0.5
        struct = float(row[3]) if row[3] is not None else 0.5
        if domain not in domain_data:
            domain_data[domain] = {"correctness": [], "grounding": [], "structure": []}
        domain_data[domain]["correctness"].append(corr)
        domain_data[domain]["grounding"].append(grnd)
        domain_data[domain]["structure"].append(struct)

    for domain, scores in domain_data.items():
        avg_corr = sum(scores["correctness"]) / len(scores["correctness"])
        avg_grnd = sum(scores["grounding"]) / len(scores["grounding"])
        avg_stru = sum(scores["structure"]) / len(scores["structure"])
        q_count = len(scores["correctness"])
        weak_count = sum(1 for c in scores["correctness"] if c < 0.5)

        # Fetch current facts row
        existing = await db.execute(text("""
            SELECT sessions_practiced, questions_answered, correct_count, weak_count,
                   avg_correctness, sm2_interval_days, sm2_ease_factor, sm2_repetitions
            FROM candidate_topic_facts
            WHERE candidate_id = :cid AND domain_code = :domain
        """), {"cid": candidate_id, "domain": domain})
        existing_row = existing.fetchone()

        now = datetime.now(timezone.utc)
        sm2_q = avg_corr * 5.0  # convert [0,1] → [0,5] for SM-2

        if existing_row:
            prev_sessions = existing_row[0]
            prev_q = existing_row[1]
            prev_corr = existing_row[2]
            prev_weak = existing_row[3]
            prev_avg = float(existing_row[4]) if existing_row[4] is not None else avg_corr
            sm2_int = existing_row[5]
            sm2_ease = float(existing_row[6])
            sm2_reps = existing_row[7]

            new_sessions = prev_sessions + 1
            new_q_total = prev_q + q_count
            new_corr_total = prev_corr + sum(1 for c in scores["correctness"] if c >= 0.5)
            new_weak_total = prev_weak + weak_count
            new_avg_corr = ((prev_avg * prev_q) + (avg_corr * q_count)) / new_q_total
            new_avg_grnd = avg_grnd
            new_avg_stru = avg_stru

            new_interval, new_ease, new_reps, next_review = _sm2_update(
                sm2_int, sm2_ease, sm2_reps, sm2_q
            )
            mastery = _compute_mastery(new_sessions, new_avg_corr)

            await db.execute(text("""
                UPDATE candidate_topic_facts SET
                    sessions_practiced = :sessions,
                    questions_answered = :q_total,
                    correct_count = :corr,
                    weak_count = :weak,
                    avg_correctness = :avg_corr,
                    avg_grounding = :avg_grnd,
                    avg_structure = :avg_stru,
                    last_practiced_at = :now,
                    mastery_status = :mastery,
                    mastery_updated_at = :now,
                    sm2_interval_days = :sm2_int,
                    sm2_ease_factor = :sm2_ease,
                    sm2_repetitions = :sm2_reps,
                    next_review_at = :next_review,
                    updated_at = :now
                WHERE candidate_id = :cid AND domain_code = :domain
            """), {
                "sessions": new_sessions, "q_total": new_q_total,
                "corr": new_corr_total, "weak": new_weak_total,
                "avg_corr": new_avg_corr, "avg_grnd": new_avg_grnd, "avg_stru": new_avg_stru,
                "now": now, "mastery": mastery,
                "sm2_int": new_interval, "sm2_ease": new_ease, "sm2_reps": new_reps,
                "next_review": next_review, "cid": candidate_id, "domain": domain,
            })
        else:
            new_interval, new_ease, new_reps, next_review = _sm2_update(1, 2.5, 0, sm2_q)
            mastery = _compute_mastery(1, avg_corr)
            corr_count = sum(1 for c in scores["correctness"] if c >= 0.5)

            await db.execute(text("""
                INSERT INTO candidate_topic_facts
                (candidate_id, domain_code, sessions_practiced, questions_answered,
                 correct_count, weak_count, avg_correctness, avg_grounding, avg_structure,
                 last_practiced_at, mastery_status, mastery_updated_at,
                 sm2_interval_days, sm2_ease_factor, sm2_repetitions, next_review_at)
                VALUES
                (:cid, :domain, 1, :q_count, :corr, :weak,
                 :avg_corr, :avg_grnd, :avg_stru,
                 :now, :mastery, :now,
                 :sm2_int, :sm2_ease, :sm2_reps, :next_review)
            """), {
                "cid": candidate_id, "domain": domain,
                "q_count": q_count, "corr": corr_count, "weak": weak_count,
                "avg_corr": avg_corr, "avg_grnd": avg_grnd, "avg_stru": avg_stru,
                "now": now, "mastery": mastery,
                "sm2_int": new_interval, "sm2_ease": new_ease, "sm2_reps": new_reps,
                "next_review": next_review,
            })

    await db.commit()
    await _generate_inferences(db, candidate_id)


async def _generate_inferences(db: AsyncSession, candidate_id: str) -> None:
    """
    Generate inferences from current facts. Each inference includes the supporting
    facts as evidence_json so the user/UI can see why the inference was made.
    Invalidates inferences that contradict new facts.
    """
    facts = await db.execute(text("""
        SELECT domain_code, sessions_practiced, avg_correctness, mastery_status,
               weak_count, questions_answered
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    fact_rows = facts.fetchall()

    now = datetime.now(timezone.utc)

    for row in fact_rows:
        domain, sessions, avg_corr, mastery, weak_count, q_total = row
        if avg_corr is None:
            continue

        avg_corr = float(avg_corr)
        weak_rate = weak_count / q_total if q_total > 0 else 0.0

        # Inference: knowledge gap
        if avg_corr < 0.5 and sessions >= 2:
            evidence = {
                "domain": domain, "sessions_practiced": sessions,
                "avg_correctness": round(avg_corr, 3),
                "weak_question_rate": round(weak_rate, 3),
            }
            confidence = "high" if avg_corr < 0.35 else "medium"
            await _upsert_inference(db, candidate_id, domain, "knowledge_gap",
                f"Consistent low correctness in {domain} ({avg_corr:.0%} avg over {sessions} sessions) "
                "suggests a knowledge gap that needs targeted practice.",
                evidence, confidence, now)

        # Inference: improvement trend (requires previous inference to compare — approximate via mastery)
        if mastery in ("proficient", "mastered_for_now") and sessions >= 3:
            evidence = {
                "domain": domain, "sessions_practiced": sessions,
                "mastery_status": mastery, "avg_correctness": round(avg_corr, 3),
            }
            await _upsert_inference(db, candidate_id, domain, "improvement_trend",
                f"Mastery level '{mastery}' in {domain} across {sessions} sessions indicates "
                "sustained improvement. Continue with harder questions.",
                evidence, "medium", now)

        # Invalidate stale knowledge_gap inferences if avg_corr is now good
        if avg_corr >= 0.70:
            await db.execute(text("""
                UPDATE candidate_inferences
                SET invalidated_at = :now
                WHERE candidate_id = :cid
                  AND domain_code = :domain
                  AND inference_type = 'knowledge_gap'
                  AND invalidated_at IS NULL
            """), {"now": now, "cid": candidate_id, "domain": domain})

    await db.commit()


async def _upsert_inference(
    db: AsyncSession, candidate_id: str, domain: Optional[str],
    itype: str, text_: str, evidence: dict, confidence: str, now: datetime
) -> None:
    existing = await db.execute(text("""
        SELECT id FROM candidate_inferences
        WHERE candidate_id = :cid
          AND (domain_code = :domain OR (domain_code IS NULL AND :domain IS NULL))
          AND inference_type = :itype
          AND invalidated_at IS NULL
    """), {"cid": candidate_id, "domain": domain, "itype": itype})
    row = existing.fetchone()

    import json
    if row:
        await db.execute(text("""
            UPDATE candidate_inferences
            SET inference_text = :text, evidence_json = :ev, confidence = :conf, generated_at = :now
            WHERE id = :id
        """), {"text": text_, "ev": json.dumps(evidence), "conf": confidence, "now": now, "id": row[0]})
    else:
        await db.execute(text("""
            INSERT INTO candidate_inferences
            (candidate_id, domain_code, inference_type, inference_text, evidence_json, confidence, generated_at)
            VALUES (:cid, :domain, :itype, :text, :ev, :conf, :now)
        """), {
            "cid": candidate_id, "domain": domain, "itype": itype,
            "text": text_, "ev": json.dumps(evidence), "conf": confidence, "now": now,
        })


async def get_candidate_memory_summary(
    db: AsyncSession, candidate_id: str
) -> dict:
    """Return facts + active inferences for the candidate — used by profile/prep services."""
    facts_rows = await db.execute(text("""
        SELECT domain_code, sessions_practiced, avg_correctness, mastery_status,
               next_review_at, sm2_interval_days
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
        ORDER BY avg_correctness ASC NULLS LAST
    """), {"cid": candidate_id})
    facts = [dict(r._mapping) for r in facts_rows.fetchall()]

    inf_rows = await db.execute(text("""
        SELECT domain_code, inference_type, inference_text, confidence, generated_at
        FROM candidate_inferences
        WHERE candidate_id = :cid AND invalidated_at IS NULL
        ORDER BY generated_at DESC
        LIMIT 20
    """), {"cid": candidate_id})
    inferences = [dict(r._mapping) for r in inf_rows.fetchall()]

    return {"facts": facts, "inferences": inferences}
