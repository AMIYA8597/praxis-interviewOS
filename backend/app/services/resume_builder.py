"""
Resume Builder — Phase 80 (Tailored Resume Draft).

Generates a tailored resume draft grounded entirely in the candidate's verified evidence:
projects, experiences, skills, and STAR stories. Every bullet produced by the LLM MUST
reference an evidence_source_id from the candidate profile — no fabricated achievements.

CRITICAL CONSTRAINT: This service is for PREPARATION only. Output is a practice draft to
help the candidate articulate their real experience — it does NOT submit applications and
must never invent metrics or technologies not present in the source evidence.
"""
import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions import NotFoundError, ServiceUnavailableError

logger = logging.getLogger(__name__)


async def draft_tailored_resume(
    db: AsyncSession,
    candidate_id: str,
    job_id: str,
    gateway_router,
    routing_ctx,
) -> dict:
    """
    Generate a tailored resume draft for the given candidate + job pair.

    Returns:
        {
            "candidate_id": str,
            "job_id": str,
            "role_title": str,
            "company_name": str,
            "summary": str,          # 2-sentence professional summary
            "bullets": [             # ordered list of tailored bullets
                {
                    "original": str | None,
                    "improved": str,
                    "jd_target": str,        # which JD requirement this covers
                    "evidence_source_id": str,
                    "evidence_type": str,    # project | experience | skill | story
                }
            ],
            "evidence_count": int,
        }
    """
    # ── 1. Fetch candidate profile ─────────────────────────────────────────────
    cand_row = await db.execute(
        text("SELECT full_name, headline, years_experience FROM candidates WHERE id = :cid"),
        {"cid": candidate_id},
    )
    candidate = cand_row.mappings().first()
    if not candidate:
        raise NotFoundError("Candidate")

    # ── 2. Fetch job details + blueprint ──────────────────────────────────────
    job_row = await db.execute(
        text("""
            SELECT j.role_title, j.company_name, j.raw_jd_text,
                   jb.summary AS jb_summary, jb.top_skills
            FROM jobs j
            LEFT JOIN job_blueprints jb ON jb.job_id = j.id
            WHERE j.id = :jid AND j.candidate_id = :cid
        """),
        {"jid": job_id, "cid": candidate_id},
    )
    job = job_row.mappings().first()
    if not job:
        raise NotFoundError("Job")

    # ── 3. Collect candidate evidence ─────────────────────────────────────────
    evidence_items: list[dict] = []

    # Projects (highest fidelity — verified by user)
    proj_rows = await db.execute(
        text("""
            SELECT id, name, summary, problem, architecture, tech_stack, metrics,
                   confidence, verified_by_user
            FROM candidate_projects WHERE candidate_id = :cid
            ORDER BY verified_by_user DESC, confidence DESC NULLS LAST
            LIMIT 10
        """),
        {"cid": candidate_id},
    )
    for r in proj_rows.mappings().fetchall():
        evidence_items.append({
            "id": str(r["id"]),
            "type": "project",
            "content": (
                f"Project: {r['name']} | "
                f"Summary: {r.get('summary') or ''} | "
                f"Problem: {r.get('problem') or ''} | "
                f"Architecture: {r.get('architecture') or ''} | "
                f"Tech stack: {json.dumps(r.get('tech_stack') or [])} | "
                f"Metrics: {r.get('metrics') or ''}"
            ),
        })

    # Experiences
    exp_rows = await db.execute(
        text("""
            SELECT id, company, title, start_date, end_date, achievements
            FROM candidate_experiences WHERE candidate_id = :cid
            ORDER BY start_date DESC NULLS LAST
            LIMIT 6
        """),
        {"cid": candidate_id},
    )
    for r in exp_rows.mappings().fetchall():
        evidence_items.append({
            "id": str(r["id"]),
            "type": "experience",
            "content": (
                f"Role: {r['title']} at {r['company']} | "
                f"Period: {r.get('start_date','')} – {r.get('end_date','present')} | "
                f"Achievements: {json.dumps(r.get('achievements') or [])}"
            ),
        })

    # Skills (with proficiency and years)
    skill_rows = await db.execute(
        text("""
            SELECT cs.id, s.name, cs.proficiency, cs.years_used, cs.evidence_source
            FROM candidate_skills cs
            JOIN skills s ON s.id = cs.skill_id
            WHERE cs.candidate_id = :cid
            ORDER BY cs.years_used DESC NULLS LAST
            LIMIT 15
        """),
        {"cid": candidate_id},
    )
    for r in skill_rows.mappings().fetchall():
        evidence_items.append({
            "id": str(r["id"]),
            "type": "skill",
            "content": (
                f"Skill: {r['name']} | "
                f"Proficiency: {r.get('proficiency') or 'intermediate'} | "
                f"Years used: {r.get('years_used') or 'unknown'}"
            ),
        })

    # STAR stories
    story_rows = await db.execute(
        text("""
            SELECT id, situation, task, action, result, competency_tags
            FROM stories WHERE candidate_id = :cid
            LIMIT 8
        """),
        {"cid": candidate_id},
    )
    for r in story_rows.mappings().fetchall():
        evidence_items.append({
            "id": str(r["id"]),
            "type": "story",
            "content": (
                f"STAR | Situation: {r.get('situation') or ''} | "
                f"Task: {r.get('task') or ''} | "
                f"Action: {r.get('action') or ''} | "
                f"Result: {r.get('result') or ''}"
            ),
        })

    if not evidence_items:
        raise ServiceUnavailableError(
            "No verified evidence found. Complete your profile (projects, experiences, skills) first."
        )

    # ── 4. Fetch JD requirements (Phase 59 graph if available) ────────────────
    req_rows = await db.execute(
        text("""
            SELECT requirement_text, domain_code, importance
            FROM jd_requirement_graph WHERE job_id = :jid
            ORDER BY (importance = 'required') DESC
            LIMIT 20
        """),
        {"jid": job_id},
    )
    requirements = req_rows.mappings().fetchall()

    if requirements:
        jd_req_text = "\n".join(
            f"- [{r['importance'].upper()}] {r['requirement_text']}"
            + (f" (domain: {r['domain_code']})" if r.get("domain_code") else "")
            for r in requirements
        )
    else:
        # Fall back to raw JD text (truncated)
        jd_req_text = (job.get("raw_jd_text") or "")[:2000]

    # ── 5. Build LLM prompt ───────────────────────────────────────────────────
    from pydantic import BaseModel
    from praxis_ai_gateway.prompt_builder import PromptBuilder

    class _Bullet(BaseModel):
        original: Optional[str] = None
        improved: str
        jd_target: str
        evidence_source_id: str
        evidence_type: str

    class _TailoredResume(BaseModel):
        summary: str
        bullets: list[_Bullet]

    builder = PromptBuilder()
    builder.add_system(
        "You are a professional resume writer helping a candidate tailor their resume "
        f"for the role: {job.get('role_title','')} at {job.get('company_name','')}.\n\n"
        "ABSOLUTE CONSTRAINTS:\n"
        "1. Every bullet MUST reference an evidence_source_id from the provided evidence list.\n"
        "2. Never invent achievements, metrics, or technologies not present in the evidence.\n"
        "3. Improve phrasing and highlight JD-relevant impact, but never fabricate anything.\n"
        "4. Use action verbs and quantified outcomes where the evidence already has them.\n"
        "5. Map each bullet to the most relevant JD requirement in jd_target.\n"
        "6. Write the summary in 2 sentences: who the candidate is and their strongest value-prop.\n"
        "Generate 6-10 high-impact bullets covering the most important JD requirements."
    )
    builder.add_untrusted(
        "candidate_evidence",
        "candidate_profile",
        json.dumps(evidence_items, indent=2)[:6000],
    )
    builder.add_untrusted("jd_requirements", "job_description", jd_req_text[:2000])
    builder.add_output_schema(_TailoredResume)

    try:
        call_result = await gateway_router.route(
            "reasoning",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=_TailoredResume,
        )
        draft: _TailoredResume = call_result.result
    except Exception as exc:
        logger.error("resume_builder_llm_failed: %s", exc, extra={"candidate_id": candidate_id})
        raise ServiceUnavailableError("Resume draft generation temporarily unavailable")

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "role_title": job.get("role_title"),
        "company_name": job.get("company_name"),
        "summary": draft.summary,
        "bullets": [b.model_dump() for b in draft.bullets],
        "evidence_count": len(evidence_items),
    }
