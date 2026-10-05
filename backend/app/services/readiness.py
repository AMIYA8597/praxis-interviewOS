"""
Phase 45-46: Preparation engine and readiness model.

Computes candidate_readiness by aggregating scores from completed practice sessions
and study reviews, then generates an ordered preparation_plans based on weakest areas.
No hardcoded scores — everything is derived from real session data.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_READINESS_WEIGHTS = {
    "technical_score": 0.30,
    "system_design_score": 0.20,
    "behavioral_score": 0.20,
    "communication_score": 0.15,
    "grounding_score": 0.10,
    "jd_coverage_score": 0.05,
}


async def compute_readiness(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
) -> dict:
    """
    Aggregate real session scores from practice_sessions and session_turns
    into a candidate_readiness row. Returns the upserted row as a dict.

    Scores are only meaningful once the candidate has >= 1 completed session.
    If no data exists, returns None so the caller knows there is no score yet.
    """
    params: dict = {"candidate_id": str(candidate_id)}

    # Aggregate turn-level scores for this candidate
    score_sql = """
        SELECT
            AVG(CASE WHEN ps.interview_type IN ('technical','mixed') THEN (st.score_json->>'correctness')::float END)         AS technical_score,
            AVG(CASE WHEN ps.interview_type = 'system_design'        THEN (st.score_json->>'overall')::float END)             AS system_design_score,
            AVG(CASE WHEN ps.interview_type = 'behavioral'           THEN (st.score_json->>'overall')::float END)             AS behavioral_score,
            AVG((st.score_json->>'structure')::float)                                                                          AS communication_score,
            AVG((st.score_json->>'grounding')::float)                                                                         AS grounding_score,
            COUNT(DISTINCT ps.id)                                                                                              AS session_count
        FROM session_turns st
        JOIN practice_sessions ps ON ps.id = st.session_id
        WHERE ps.candidate_id = :candidate_id
          AND st.speaker = 'candidate'
          AND st.score_json IS NOT NULL
          AND ps.status = 'completed'
    """
    if job_id:
        score_sql += " AND ps.job_id = :job_id"
        params["job_id"] = str(job_id)

    row = (await db.execute(text(score_sql), params)).mappings().first()
    if not row or (row["session_count"] or 0) == 0:
        return None

    def _f(v) -> Optional[float]:
        return round(float(v) * 100, 2) if v is not None else None

    t = _f(row["technical_score"])
    sd = _f(row["system_design_score"])
    beh = _f(row["behavioral_score"])
    com = _f(row["communication_score"])
    grd = _f(row["grounding_score"])

    # JD coverage: fraction of job requirement keywords found in candidate answers
    jd_cov: Optional[float] = None
    if job_id:
        cov_sql = """
            SELECT
                COUNT(DISTINCT jr.id) FILTER (
                    WHERE EXISTS (
                        SELECT 1 FROM session_turns st2
                        JOIN practice_sessions ps2 ON ps2.id = st2.session_id
                        WHERE ps2.candidate_id = :candidate_id
                          AND ps2.job_id = :job_id
                          AND ps2.status = 'completed'
                          AND st2.speaker = 'candidate'
                          AND st2.text ILIKE '%' || jr.requirement_text || '%'
                    )
                )::float / NULLIF(COUNT(DISTINCT jr.id), 0) AS coverage
            FROM job_requirements jr
            WHERE jr.job_id = :job_id
        """
        cov_row = (await db.execute(text(cov_sql), params)).first()
        if cov_row and cov_row[0] is not None:
            jd_cov = round(float(cov_row[0]) * 100, 2)

    # Weighted overall
    scores = {
        "technical_score": t,
        "system_design_score": sd,
        "behavioral_score": beh,
        "communication_score": com,
        "grounding_score": grd,
        "jd_coverage_score": jd_cov,
    }
    weighted_sum = 0.0
    weight_sum = 0.0
    for key, w in _READINESS_WEIGHTS.items():
        v = scores[key]
        if v is not None:
            weighted_sum += (v / 100) * w
            weight_sum += w
    overall = round((weighted_sum / weight_sum) * 100, 2) if weight_sum > 0 else None

    confidence = (
        "high" if (row["session_count"] or 0) >= 5
        else "medium" if (row["session_count"] or 0) >= 2
        else "low"
    )

    # Weakest domain
    domain_scores = {
        "TECHNICAL": t, "SYSTEM_DESIGN": sd, "BEHAVIORAL": beh,
    }
    weakest = min(
        ((k, v) for k, v in domain_scores.items() if v is not None),
        key=lambda x: x[1],
        default=(None, None),
    )[0]

    recommended = None
    if weakest == "TECHNICAL":
        recommended = "Practice 3+ technical drills focusing on DSA and correctness."
    elif weakest == "SYSTEM_DESIGN":
        recommended = "Complete 2+ system design mock interviews."
    elif weakest == "BEHAVIORAL":
        recommended = "Practice STAR-method answers for leadership and conflict scenarios."

    upsert_sql = """
        INSERT INTO candidate_readiness
          (candidate_id, job_id, overall_score, confidence, technical_score,
           system_design_score, behavioral_score, communication_score,
           grounding_score, jd_coverage_score, weakest_domain,
           recommended_action, component_detail)
        VALUES
          (:candidate_id, :job_id, :overall, :confidence, :technical,
           :sd, :beh, :com, :grd, :jd_cov, :weakest, :recommended, :detail::jsonb)
        ON CONFLICT (candidate_id, job_id)
        DO UPDATE SET
          overall_score = EXCLUDED.overall_score,
          confidence = EXCLUDED.confidence,
          technical_score = EXCLUDED.technical_score,
          system_design_score = EXCLUDED.system_design_score,
          behavioral_score = EXCLUDED.behavioral_score,
          communication_score = EXCLUDED.communication_score,
          grounding_score = EXCLUDED.grounding_score,
          jd_coverage_score = EXCLUDED.jd_coverage_score,
          weakest_domain = EXCLUDED.weakest_domain,
          recommended_action = EXCLUDED.recommended_action,
          component_detail = EXCLUDED.component_detail,
          computed_at = now()
        RETURNING *
    """
    import json
    result_row = (await db.execute(text(upsert_sql), {
        "candidate_id": str(candidate_id),
        "job_id": str(job_id) if job_id else None,
        "overall": overall,
        "confidence": confidence,
        "technical": t,
        "sd": sd,
        "beh": beh,
        "com": com,
        "grd": grd,
        "jd_cov": jd_cov,
        "weakest": weakest,
        "recommended": recommended,
        "detail": json.dumps(scores),
    })).mappings().first()
    await db.commit()
    return dict(result_row)


async def generate_preparation_plan(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
) -> dict:
    """
    Generate an ordered list of practice sessions based on readiness gaps.
    Sessions are ordered weakest-area-first. Returns the upserted plan row.
    """
    readiness = await compute_readiness(db, candidate_id, job_id)

    plan_sessions = []
    if readiness is None:
        plan_sessions = [
            {"order": 1, "type": "mock_interview", "interview_type": "behavioral", "difficulty": "warmup", "rationale": "Start with a warmup behavioral session to establish baseline."},
            {"order": 2, "type": "mock_interview", "interview_type": "technical", "difficulty": "warmup", "rationale": "Baseline technical session."},
            {"order": 3, "type": "drill", "interview_type": "behavioral", "difficulty": "standard", "rationale": "STAR method practice."},
        ]
    else:
        order = 1
        # Prioritise weakest area first
        area_order = sorted(
            [
                ("technical", readiness.get("technical_score") or 0),
                ("system_design", readiness.get("system_design_score") or 0),
                ("behavioral", readiness.get("behavioral_score") or 0),
            ],
            key=lambda x: x[1],
        )
        for area, score in area_order:
            diff = "standard" if score >= 60 else "warmup"
            plan_sessions.append({
                "order": order,
                "type": "mock_interview",
                "interview_type": area,
                "difficulty": diff,
                "rationale": f"Score is {score:.0f}/100 — needs improvement." if score < 70 else f"Maintain {area} skills.",
            })
            order += 1

    import json
    upsert_sql = """
        INSERT INTO preparation_plans (candidate_id, job_id, plan_sessions, is_active, completed_count)
        VALUES (:candidate_id, :job_id, :sessions::jsonb, true, 0)
        ON CONFLICT (candidate_id, job_id)
        DO UPDATE SET
          plan_sessions = EXCLUDED.plan_sessions,
          is_active = true,
          generated_at = now()
        RETURNING *
    """
    row = (await db.execute(text(upsert_sql), {
        "candidate_id": str(candidate_id),
        "job_id": str(job_id) if job_id else None,
        "sessions": json.dumps(plan_sessions),
    })).mappings().first()
    await db.commit()
    return dict(row)
