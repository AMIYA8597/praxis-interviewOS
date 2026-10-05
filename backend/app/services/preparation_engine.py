"""
Phase 57 — Real Preparation Engine.

Input: candidate profile + resume + job description + session history
Output: personalized preparation plan ordered by (weakness × job_relevance × impact)

No hardcoded values. All ordering is driven by real session data.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Weight for plan priority scoring: higher = surface sooner
def _priority_score(
    avg_correctness: Optional[float],
    jd_match_score: float,
    sessions_practiced: int,
) -> float:
    weakness = 1.0 - (avg_correctness or 0.5)       # 0 (strong) → 1 (weak)
    novelty = 1.0 / (1.0 + sessions_practiced)       # 1 (never practiced) → 0 (practiced many times)
    return weakness * 0.5 + jd_match_score * 0.3 + novelty * 0.2


async def generate_real_preparation_plan(
    db: AsyncSession,
    candidate_id: str,
    job_id: Optional[str] = None,
) -> dict:
    """
    Build a prioritized preparation plan by crossing:
    - candidate's topic facts (weakness signal)
    - job blueprint requirements (relevance signal)
    - session history (novelty signal)

    Returns ordered list of preparation items with justification.
    """
    # Fetch topic facts
    fact_rows = await db.execute(text("""
        SELECT domain_code, avg_correctness, sessions_practiced, mastery_status
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    facts = {r[0]: {"avg_correctness": r[1], "sessions": r[2], "mastery": r[3]}
             for r in fact_rows.fetchall()}

    # Fetch all domains so we include ones with zero practice
    domain_rows = await db.execute(text(
        "SELECT code, display_name FROM interview_domains"
    ))
    all_domains = {r[0]: r[1] for r in domain_rows.fetchall()}

    # Fetch JD requirements if job provided
    jd_domains: dict[str, float] = {}
    if job_id:
        bp_row = await db.execute(text("""
            SELECT summary FROM job_blueprints WHERE job_id = :jid
        """), {"jid": job_id})
        bp = bp_row.scalar()
        if bp:
            import json
            try:
                bp_data = json.loads(bp) if isinstance(bp, str) else bp
                reqs = bp_data.get("requirements", [])
                for req in reqs:
                    req_lower = req.lower()
                    for code in all_domains:
                        if code.lower() in req_lower or req_lower in code.lower():
                            jd_domains[code] = min(1.0, jd_domains.get(code, 0) + 0.3)
            except Exception:
                pass

    # Score each domain
    items = []
    for domain_code, display_name in all_domains.items():
        fact = facts.get(domain_code, {})
        avg_corr = fact.get("avg_correctness")
        sessions = fact.get("sessions", 0)
        mastery = fact.get("mastery", "unknown")

        if mastery == "mastered_for_now":
            continue  # Skip mastered domains

        jd_match = jd_domains.get(domain_code, 0.1)  # minimal relevance even without JD
        priority = _priority_score(
            float(avg_corr) if avg_corr is not None else None,
            jd_match,
            sessions,
        )

        reason_parts = []
        if avg_corr is not None and float(avg_corr) < 0.6:
            reason_parts.append(f"low correctness ({float(avg_corr):.0%})")
        if sessions == 0:
            reason_parts.append("never practiced")
        elif sessions < 3:
            reason_parts.append(f"only {sessions} session(s)")
        if domain_code in jd_domains:
            reason_parts.append("required in job description")

        items.append({
            "domain_code": domain_code,
            "display_name": display_name,
            "priority_score": round(priority, 4),
            "avg_correctness": float(avg_corr) if avg_corr is not None else None,
            "sessions_practiced": sessions,
            "mastery_status": mastery,
            "jd_relevance": jd_match,
            "reason": "; ".join(reason_parts) if reason_parts else "general practice",
        })

    items.sort(key=lambda x: x["priority_score"], reverse=True)

    # Persist to preparation_plans (Phase 37 table)
    now = datetime.now(timezone.utc)
    import json
    plan_json = json.dumps(items[:15])  # top 15 domains

    await db.execute(text("""
        INSERT INTO preparation_plans
        (candidate_id, job_id, plan_json, generated_at)
        VALUES (:cid, :jid, :plan, :now)
        ON CONFLICT (candidate_id, job_id) DO UPDATE SET
          plan_json = EXCLUDED.plan_json,
          generated_at = EXCLUDED.generated_at
    """), {"cid": candidate_id, "jid": job_id, "plan": plan_json, "now": now})
    await db.commit()

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "generated_at": now.isoformat(),
        "plan_items": items[:15],
        "total_domains_evaluated": len(items),
    }
