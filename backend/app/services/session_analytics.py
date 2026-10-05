"""
Phase 66-70 — Daily Loop, Session Comparison, Weakness Detection,
               Mastery Management, Knowledge Decay.

All analysis is from real session data. No fabricated metrics.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Phase 66: Daily Interview Loop ──────────────────────────────────────────

async def get_daily_recommendation(
    db: AsyncSession, candidate_id: str, job_id: Optional[str] = None
) -> dict:
    """
    Return today's recommended practice focus based on:
    1. Topics due for SM-2 review (next_review_at <= now)
    2. Weakest topic not practiced in 3+ days
    3. JD gap if job provided
    """
    now = datetime.now(timezone.utc)

    # SM-2 due for review
    due_rows = await db.execute(text("""
        SELECT domain_code, mastery_status, avg_correctness, next_review_at
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
          AND next_review_at IS NOT NULL
          AND next_review_at <= :now
        ORDER BY next_review_at ASC
        LIMIT 5
    """), {"cid": candidate_id, "now": now})
    due_review = [dict(r._mapping) for r in due_rows.fetchall()]

    # Weakest domain not recently practiced
    weak_rows = await db.execute(text("""
        SELECT domain_code, avg_correctness, last_practiced_at
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
          AND avg_correctness IS NOT NULL
          AND avg_correctness < 0.65
          AND (last_practiced_at IS NULL OR last_practiced_at < NOW() - INTERVAL '3 days')
        ORDER BY avg_correctness ASC
        LIMIT 3
    """), {"cid": candidate_id})
    weakest = [dict(r._mapping) for r in weak_rows.fetchall()]

    # JD gaps if job provided
    jd_gaps = []
    if job_id:
        gap_rows = await db.execute(text("""
            SELECT g.requirement_text, g.domain_code
            FROM candidate_jd_evidence e
            JOIN jd_requirement_graph g ON g.id = e.requirement_id
            WHERE e.candidate_id = :cid AND g.job_id = :jid AND e.covered = FALSE
              AND g.importance = 'required'
            LIMIT 3
        """), {"cid": candidate_id, "jid": job_id})
        jd_gaps = [dict(r._mapping) for r in gap_rows.fetchall()]

    recommendations = []
    if due_review:
        recommendations.append({
            "type": "spaced_repetition_review",
            "domains": [r["domain_code"] for r in due_review],
            "reason": f"{len(due_review)} domain(s) are due for spaced repetition review.",
            "priority": 1,
        })
    if weakest:
        recommendations.append({
            "type": "weakness_practice",
            "domains": [r["domain_code"] for r in weakest],
            "reason": "Low correctness in these areas, not practiced recently.",
            "priority": 2,
        })
    if jd_gaps:
        recommendations.append({
            "type": "jd_gap",
            "domains": [r.get("domain_code") for r in jd_gaps if r.get("domain_code")],
            "requirements": [r["requirement_text"] for r in jd_gaps],
            "reason": "Required by job description but not yet covered.",
            "priority": 1,
        })

    if not recommendations:
        recommendations.append({
            "type": "general_practice",
            "reason": "All topics are up to date. Practice any domain to maintain mastery.",
            "priority": 3,
        })

    return {
        "date": now.date().isoformat(),
        "recommendations": sorted(recommendations, key=lambda x: x["priority"]),
    }


# ── Phase 67: Session Comparison ────────────────────────────────────────────

async def snapshot_session_performance(
    db: AsyncSession, candidate_id: str, session_id: str
) -> dict:
    """Capture a performance snapshot for comparison against future sessions."""
    agg = await db.execute(text("""
        SELECT
          AVG(ts.overall)      AS overall_score,
          AVG(ts.correctness)  AS correctness,
          AVG(ts.structure)    AS structure,
          AVG(ts.grounding)    AS grounding,
          AVG(ts.specificity)  AS specificity,
          AVG(ts.conciseness)  AS conciseness,
          COUNT(st.id)         AS turns_count
        FROM session_turns st
        JOIN turn_scores ts ON ts.turn_id = st.id
        WHERE st.session_id = :sid AND st.speaker = 'candidate'
    """), {"sid": session_id})
    row = agg.fetchone()

    now = datetime.now(timezone.utc)
    vals = dict(row._mapping) if row else {}

    await db.execute(text("""
        INSERT INTO session_performance_snapshots
        (candidate_id, session_id, overall_score, correctness, structure,
         grounding, specificity, conciseness, turns_count, snapped_at)
        VALUES (:cid, :sid, :overall, :corr, :struct, :grnd, :spec, :conc, :turns, :now)
        ON CONFLICT (session_id) DO UPDATE SET
          overall_score = EXCLUDED.overall_score,
          correctness = EXCLUDED.correctness,
          structure = EXCLUDED.structure,
          grounding = EXCLUDED.grounding,
          specificity = EXCLUDED.specificity,
          conciseness = EXCLUDED.conciseness,
          turns_count = EXCLUDED.turns_count,
          snapped_at = EXCLUDED.snapped_at
    """), {
        "cid": candidate_id, "sid": session_id,
        "overall": vals.get("overall_score"), "corr": vals.get("correctness"),
        "struct": vals.get("structure"), "grnd": vals.get("grounding"),
        "spec": vals.get("specificity"), "conc": vals.get("conciseness"),
        "turns": vals.get("turns_count", 0), "now": now,
    })
    await db.commit()
    return {**vals, "session_id": session_id, "snapped_at": now.isoformat()}


async def compare_sessions(db: AsyncSession, candidate_id: str) -> dict:
    """
    Compare last two sessions. Returns per-dimension delta with improved/stable/regressed labels.
    """
    snap_rows = await db.execute(text("""
        SELECT session_id, overall_score, correctness, structure, grounding,
               specificity, conciseness, turns_count, snapped_at
        FROM session_performance_snapshots
        WHERE candidate_id = :cid
        ORDER BY snapped_at DESC
        LIMIT 2
    """), {"cid": candidate_id})
    snaps = snap_rows.fetchall()

    if len(snaps) < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 sessions to compare."}

    latest = dict(snaps[0]._mapping)
    previous = dict(snaps[1]._mapping)

    dims = ["overall_score", "correctness", "structure", "grounding", "specificity", "conciseness"]
    comparison = {}
    for d in dims:
        cur = float(latest[d]) if latest[d] is not None else None
        prev = float(previous[d]) if previous[d] is not None else None
        if cur is None or prev is None:
            comparison[d] = {"status": "no_data"}
            continue
        delta = cur - prev
        status = "improved" if delta > 0.02 else ("regressed" if delta < -0.02 else "stable")
        comparison[d] = {
            "current": round(cur, 3),
            "previous": round(prev, 3),
            "delta": round(delta, 3),
            "status": status,
        }

    return {
        "latest_session": str(latest["session_id"]),
        "previous_session": str(previous["session_id"]),
        "comparison": comparison,
    }


# ── Phase 68: Weakness Detection ────────────────────────────────────────────

async def detect_and_persist_weaknesses(
    db: AsyncSession, candidate_id: str
) -> list[dict]:
    """
    Evidence-backed weakness detection from real session data.
    Upserts into candidate_weaknesses with evidence.
    """
    # Knowledge gaps: domains with avg_correctness < 0.5 over >= 2 sessions
    gap_rows = await db.execute(text("""
        SELECT domain_code, avg_correctness, sessions_practiced, weak_count, questions_answered
        FROM candidate_topic_facts
        WHERE candidate_id = :cid AND avg_correctness < 0.5 AND sessions_practiced >= 2
    """), {"cid": candidate_id})

    now = datetime.now(timezone.utc)
    weaknesses = []

    for row in gap_rows.fetchall():
        domain, avg_corr, sessions, weak_count, q_total = row
        evidence = {
            "domain": domain,
            "avg_correctness": float(avg_corr),
            "sessions_practiced": sessions,
            "weak_question_rate": round(weak_count / q_total, 3) if q_total else 0,
        }
        severity = "high" if float(avg_corr) < 0.3 else "medium"
        await _upsert_weakness(db, candidate_id, "knowledge_gap", domain,
                               f"Persistent low correctness in {domain}: {float(avg_corr):.0%} avg over {sessions} sessions.",
                               evidence, severity, now)
        weaknesses.append({"type": "knowledge_gap", "domain": domain, "severity": severity})

    # Grounding issues: avg grounding < 0.6 overall
    grnd_row = await db.execute(text("""
        SELECT AVG(ts.grounding), COUNT(*)
        FROM turn_scores ts
        JOIN session_turns st ON st.id = ts.turn_id
        JOIN practice_sessions ps ON ps.id = st.session_id
        WHERE ps.candidate_id = :cid AND st.speaker = 'candidate' AND ts.grounding IS NOT NULL
    """), {"cid": candidate_id})
    grnd_data = grnd_row.fetchone()
    if grnd_data and grnd_data[1] >= 5 and grnd_data[0] is not None and float(grnd_data[0]) < 0.6:
        evidence = {"avg_grounding": float(grnd_data[0]), "sample_count": int(grnd_data[1])}
        await _upsert_weakness(db, candidate_id, "grounding", None,
                               f"Low grounding score ({float(grnd_data[0]):.0%}) across {grnd_data[1]} turns — "
                               "candidate makes claims not supported by verified context.",
                               evidence, "high", now)
        weaknesses.append({"type": "grounding", "severity": "high"})

    await db.commit()
    return weaknesses


async def _upsert_weakness(
    db, candidate_id, wtype, domain, description, evidence, severity, now
):
    existing = await db.execute(text("""
        SELECT id, occurrence_count FROM candidate_weaknesses
        WHERE candidate_id = :cid AND weakness_type = :wtype
          AND (domain_code = :domain OR (domain_code IS NULL AND :domain IS NULL))
    """), {"cid": candidate_id, "wtype": wtype, "domain": domain})
    row = existing.fetchone()
    if row:
        await db.execute(text("""
            UPDATE candidate_weaknesses SET
              description = :desc, evidence_json = :ev, severity = :sev,
              occurrence_count = :occ, last_observed_at = :now
            WHERE id = :id
        """), {
            "desc": description, "ev": json.dumps(evidence), "sev": severity,
            "occ": row[1] + 1, "now": now, "id": row[0],
        })
    else:
        await db.execute(text("""
            INSERT INTO candidate_weaknesses
            (candidate_id, weakness_type, domain_code, description, evidence_json, severity, first_observed_at, last_observed_at)
            VALUES (:cid, :wtype, :domain, :desc, :ev, :sev, :now, :now)
        """), {
            "cid": candidate_id, "wtype": wtype, "domain": domain,
            "desc": description, "ev": json.dumps(evidence), "sev": severity, "now": now,
        })
