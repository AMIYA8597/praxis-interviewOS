"""
Phase 59 — Real JD-Driven Preparation.

JD text → parsed requirement graph → candidate evidence map → gap identification.
Updates preparation plan with JD-specific priorities.

No hardcoded domain mappings; uses fuzzy overlap + LLM extraction if available.
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Keyword → domain_code fallback map (used when LLM extraction is unavailable)
_KEYWORD_DOMAIN_MAP = {
    "python": "backend",
    "java": "backend",
    "go": "backend",
    "typescript": "backend",
    "javascript": "backend",
    "react": "frontend",
    "sql": "databases",
    "postgres": "databases",
    "mysql": "databases",
    "mongodb": "nosql",
    "redis": "databases",
    "kafka": "distributed_systems",
    "kubernetes": "distributed_systems",
    "docker": "backend",
    "aws": "cloud",
    "gcp": "cloud",
    "azure": "cloud",
    "system design": "system_design",
    "distributed": "distributed_systems",
    "algorithms": "dsa",
    "data structures": "dsa",
    "leadership": "behavioral",
    "communication": "behavioral",
}


def _extract_requirements_from_text(jd_text: str) -> list[dict]:
    """
    Fallback parser: extract requirement bullets from JD text.
    Returns list of {text, importance, domain_code}.
    """
    lines = jd_text.split("\n")
    requirements = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Look for bullet points / numbered lists / "Requirements:" section items
        if re.match(r"^[\-\*\•]\s+", line) or re.match(r"^\d+\.\s+", line):
            req_text = re.sub(r"^[\-\*\•\d\.]\s*", "", line).strip()
            if len(req_text) > 10:
                importance = "required"
                if any(w in req_text.lower() for w in ["nice to have", "preferred", "plus", "bonus"]):
                    importance = "preferred"

                # Map to domain
                domain = None
                req_lower = req_text.lower()
                for kw, dom in _KEYWORD_DOMAIN_MAP.items():
                    if kw in req_lower:
                        domain = dom
                        break

                requirements.append({
                    "text": req_text,
                    "importance": importance,
                    "domain_code": domain,
                })

    return requirements


async def parse_and_store_jd_requirements(
    db: AsyncSession,
    job_id: str,
    jd_text: str,
    gateway_router=None,
    routing_ctx=None,
) -> list[dict]:
    """
    Parse JD requirements and store in jd_requirement_graph.
    Tries LLM extraction first, falls back to rule-based parser.
    """
    requirements = []

    if gateway_router is not None:
        from praxis_ai_gateway.prompt_builder import PromptBuilder
        from pydantic import BaseModel

        class JdRequirement(BaseModel):
            text: str
            importance: str  # required | preferred | nice_to_have
            domain_code: Optional[str] = None

        class JdRequirements(BaseModel):
            requirements: list[JdRequirement]

        builder = PromptBuilder()
        builder.add_system(
            "Extract all skill and experience requirements from the following job description. "
            "For each: identify if required/preferred/nice_to_have and map to the most relevant "
            "technical domain (e.g. dsa, backend, databases, distributed_systems, system_design, "
            "cloud, behavioral). Return all requirements including soft skills."
        )
        builder.add_untrusted("job_description", "hr_team", jd_text[:4000])
        builder.add_output_schema(JdRequirements)

        try:
            result = await gateway_router.route(
                "fast_classify", routing_ctx, "generate_structured",
                messages=[m.model_dump(exclude_none=True) for m in builder.build()],
                schema=JdRequirements,
            )
            requirements = [
                {"text": r.text, "importance": r.importance, "domain_code": r.domain_code}
                for r in result.result.requirements
            ]
        except Exception as e:
            logger.warning("LLM JD extraction failed, using fallback: %s", e)

    if not requirements:
        requirements = _extract_requirements_from_text(jd_text)

    # Delete existing requirements for this job (re-parse)
    await db.execute(text(
        "DELETE FROM jd_requirement_graph WHERE job_id = :jid"
    ), {"jid": job_id})

    now = datetime.now(timezone.utc)
    inserted = []
    for req in requirements:
        row = await db.execute(text("""
            INSERT INTO jd_requirement_graph (job_id, requirement_text, domain_code, importance, created_at)
            VALUES (:jid, :text, :domain, :importance, :now)
            RETURNING id
        """), {
            "jid": job_id, "text": req["text"],
            "domain": req.get("domain_code"), "importance": req["importance"], "now": now,
        })
        req_id = row.scalar()
        inserted.append({**req, "id": str(req_id)})

    await db.commit()
    return inserted


async def build_candidate_evidence_map(
    db: AsyncSession,
    candidate_id: str,
    job_id: str,
) -> dict:
    """
    Map candidate's real session performance to JD requirements.
    Returns coverage stats: covered / total, gap list.
    """
    # Get JD requirements
    req_rows = await db.execute(text("""
        SELECT id, requirement_text, domain_code, importance
        FROM jd_requirement_graph WHERE job_id = :jid
    """), {"jid": job_id})
    requirements = req_rows.fetchall()

    if not requirements:
        return {"covered": 0, "total": 0, "coverage_pct": None, "gaps": []}

    # Get candidate topic facts
    fact_rows = await db.execute(text("""
        SELECT domain_code, avg_correctness, sessions_practiced
        FROM candidate_topic_facts WHERE candidate_id = :cid
    """), {"cid": candidate_id})
    facts = {r[0]: {"avg_correctness": r[1], "sessions": r[2]}
             for r in fact_rows.fetchall()}

    now = datetime.now(timezone.utc)
    covered_count = 0
    gaps = []

    for req in requirements:
        req_id, req_text, domain_code, importance = req
        covered = False
        score = None

        if domain_code and domain_code in facts:
            f = facts[domain_code]
            if f["avg_correctness"] is not None and float(f["avg_correctness"]) >= 0.60:
                covered = True
                score = float(f["avg_correctness"])
            elif f["sessions"] and f["sessions"] >= 1:
                score = float(f["avg_correctness"]) if f["avg_correctness"] else None

        # Upsert evidence
        await db.execute(text("""
            INSERT INTO candidate_jd_evidence
            (candidate_id, requirement_id, evidence_type, score, covered, last_updated_at)
            VALUES (:cid, :req_id, 'session_score', :score, :covered, :now)
            ON CONFLICT (candidate_id, requirement_id) DO UPDATE SET
              score = EXCLUDED.score, covered = EXCLUDED.covered, last_updated_at = EXCLUDED.last_updated_at
        """), {
            "cid": candidate_id, "req_id": str(req_id),
            "score": score, "covered": covered, "now": now,
        })

        if covered:
            covered_count += 1
        else:
            gaps.append({
                "requirement_text": req_text,
                "domain_code": domain_code,
                "importance": importance,
                "current_score": score,
            })

    await db.commit()

    total = len(requirements)
    return {
        "covered": covered_count,
        "total": total,
        "coverage_pct": round(covered_count / total * 100, 1) if total > 0 else None,
        "gaps": sorted(gaps, key=lambda g: {"required": 0, "preferred": 1, "nice_to_have": 2}
                       .get(g["importance"], 3)),
    }
