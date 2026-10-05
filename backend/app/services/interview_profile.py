"""
Phase 56 — Personal Interview Profile.

Aggregates all scoring dimensions from real session data into a canonical
per-candidate profile. No hardcoded values; returns None for dimensions
that have no real session data yet.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Domain groups → profile score dimensions
_DSA_DOMAINS = {"dsa", "algorithms", "data_structures"}
_BACKEND_DOMAINS = {"backend", "system_design_basics", "api_design", "concurrency"}
_DB_DOMAINS = {"databases", "sql", "nosql"}
_DIST_DOMAINS = {"distributed_systems", "distributed", "cloud"}
_SYSDES_DOMAINS = {"system_design"}
_BEHAVIORAL_DOMAINS = {"behavioral", "leadership", "teamwork", "conflict"}


def _domain_to_dimension(domain_code: str) -> Optional[str]:
    d = domain_code.lower()
    if d in _DSA_DOMAINS:
        return "dsa"
    if d in _BACKEND_DOMAINS:
        return "backend"
    if d in _DB_DOMAINS:
        return "databases"
    if d in _DIST_DOMAINS:
        return "distributed"
    if d in _SYSDES_DOMAINS:
        return "system_design"
    if d in _BEHAVIORAL_DOMAINS:
        return "behavioral"
    return None


async def compute_interview_profile(
    db: AsyncSession, candidate_id: str
) -> dict:
    """
    Compute and persist the canonical interview profile from real facts.
    Returns the profile dict (all None fields = insufficient data).
    """
    # Fetch topic facts
    fact_rows = await db.execute(text("""
        SELECT domain_code, avg_correctness, avg_grounding, avg_structure, sessions_practiced
        FROM candidate_topic_facts
        WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    facts = fact_rows.fetchall()

    # Fetch communication profile
    comm_row = await db.execute(text("""
        SELECT avg_structure_score, sessions_counted
        FROM candidate_communication_profile
        WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    comm = comm_row.fetchone()

    # Fetch total session count from real practice sessions
    sess_row = await db.execute(text("""
        SELECT COUNT(*) FROM practice_sessions
        WHERE candidate_id = :cid AND status = 'completed'
    """), {"cid": candidate_id})
    total_sessions = sess_row.scalar() or 0

    # Fetch grounding aggregate across all sessions
    grnd_row = await db.execute(text("""
        SELECT AVG(ts.grounding)
        FROM turn_scores ts
        JOIN session_turns st ON st.id = ts.turn_id
        JOIN practice_sessions ps ON ps.id = st.session_id
        WHERE ps.candidate_id = :cid AND st.speaker = 'candidate'
    """), {"cid": candidate_id})
    overall_grounding = grnd_row.scalar()

    # Fetch claim counts
    claim_row = await db.execute(text("""
        SELECT
            SUM(CASE WHEN supported = TRUE THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN supported = FALSE THEN 1 ELSE 0 END) AS uncertain
        FROM session_claims sc
        JOIN practice_sessions ps ON ps.id = sc.session_id
        WHERE ps.candidate_id = :cid
    """), {"cid": candidate_id})
    claim_data = claim_row.fetchone()
    verified_claims = int(claim_data[0] or 0)
    uncertain_claims = int(claim_data[1] or 0)

    # Aggregate dimension scores from topic facts
    dim_scores: dict[str, list[float]] = {}
    for row in facts:
        domain_code, avg_corr, avg_grnd, avg_struct, sessions = row
        dim = _domain_to_dimension(domain_code)
        if dim is None or avg_corr is None:
            continue
        # Weighted aggregate: correctness 60%, grounding 25%, structure 15%
        combined = (
            float(avg_corr) * 0.60
            + float(avg_grnd or 0.5) * 0.25
            + float(avg_struct or 0.5) * 0.15
        ) * 100  # scale to 0-100
        if dim not in dim_scores:
            dim_scores[dim] = []
        dim_scores[dim].append(combined)

    def avg_or_none(values: list[float]) -> Optional[float]:
        return round(sum(values) / len(values), 1) if values else None

    dsa_score = avg_or_none(dim_scores.get("dsa", []))
    backend_score = avg_or_none(dim_scores.get("backend", []))
    db_score = avg_or_none(dim_scores.get("databases", []))
    dist_score = avg_or_none(dim_scores.get("distributed", []))
    sysdes_score = avg_or_none(dim_scores.get("system_design", []))
    behavioral_score = avg_or_none(dim_scores.get("behavioral", []))
    comm_score = round(float(comm[0]) * 100, 1) if comm and comm[0] else None
    grounding_score = round(float(overall_grounding) * 100, 1) if overall_grounding else None

    now = datetime.now(timezone.utc)

    # Fetch current version for bump
    ver_row = await db.execute(text("""
        SELECT profile_version FROM candidate_interview_profile WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    existing_ver = ver_row.scalar() or 0

    await db.execute(text("""
        INSERT INTO candidate_interview_profile
        (candidate_id, dsa_score, backend_score, databases_score, distributed_score,
         system_design_score, behavioral_score, communication_score, grounding_score,
         verified_claims_count, uncertain_claims_count, total_sessions, profile_version, computed_at)
        VALUES (:cid, :dsa, :be, :db, :dist, :sd, :beh, :comm, :grnd,
                :ver_cl, :unc_cl, :total_s, :ver, :now)
        ON CONFLICT (candidate_id) DO UPDATE SET
          dsa_score = EXCLUDED.dsa_score,
          backend_score = EXCLUDED.backend_score,
          databases_score = EXCLUDED.databases_score,
          distributed_score = EXCLUDED.distributed_score,
          system_design_score = EXCLUDED.system_design_score,
          behavioral_score = EXCLUDED.behavioral_score,
          communication_score = EXCLUDED.communication_score,
          grounding_score = EXCLUDED.grounding_score,
          verified_claims_count = EXCLUDED.verified_claims_count,
          uncertain_claims_count = EXCLUDED.uncertain_claims_count,
          total_sessions = EXCLUDED.total_sessions,
          profile_version = :ver,
          computed_at = EXCLUDED.computed_at
    """), {
        "cid": candidate_id,
        "dsa": dsa_score, "be": backend_score, "db": db_score, "dist": dist_score,
        "sd": sysdes_score, "beh": behavioral_score, "comm": comm_score, "grnd": grounding_score,
        "ver_cl": verified_claims, "unc_cl": uncertain_claims,
        "total_s": total_sessions, "ver": existing_ver + 1, "now": now,
    })
    await db.commit()

    return {
        "dsa_score": dsa_score,
        "backend_score": backend_score,
        "databases_score": db_score,
        "distributed_score": dist_score,
        "system_design_score": sysdes_score,
        "behavioral_score": behavioral_score,
        "communication_score": comm_score,
        "grounding_score": grounding_score,
        "verified_claims_count": verified_claims,
        "uncertain_claims_count": uncertain_claims,
        "total_sessions": total_sessions,
        "profile_version": existing_ver + 1,
        "computed_at": now.isoformat(),
    }


async def get_interview_profile(db: AsyncSession, candidate_id: str) -> Optional[dict]:
    row = await db.execute(text("""
        SELECT dsa_score, backend_score, databases_score, distributed_score,
               system_design_score, behavioral_score, communication_score, grounding_score,
               verified_claims_count, uncertain_claims_count, total_sessions,
               profile_version, computed_at
        FROM candidate_interview_profile
        WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    r = row.fetchone()
    if not r:
        return None
    return dict(r._mapping)
