"""
Phase 81 — "Prepare Me" Experience.
Phase 82 — Interview-Day Mode (pre-interview preparation — NOT live cheating).

Phase 81: User inputs target company/role/interview date → system generates
a structured preparation plan using all available data.

Phase 82: Interview-Day mode is PRE-interview preparation: practice mode
with time pressure, common FAANG patterns, and last-mile readiness check.
This is NOT assistance during a real employer interview. It's practice before.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import preparation_engine as prep_svc
from backend.app.services import readiness_v2 as r2_svc

router = APIRouter(tags=["prepare-me"], responses=COMMON_ERROR_RESPONSES)


class PrepareMeRequest(BaseModel):
    target_company: str
    target_role: str
    interview_date: date
    job_id: Optional[uuid.UUID] = None


@router.post("/prepare-me")
async def prepare_me(
    body: PrepareMeRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Phase 81 — "Prepare Me" Experience.

    Given target company/role/date, returns:
    - Days until interview
    - Current readiness assessment (from real sessions)
    - Prioritized preparation plan (from weakness × JD relevance × novelty)
    - Recommended daily practice schedule
    """
    now = datetime.now(timezone.utc).date()
    days_until = (body.interview_date - now).days

    if days_until < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Interview date is in the past.")

    # Get current readiness
    readiness = await r2_svc.get_readiness_v2(db, candidate["id"])

    # Get preparation plan (reuses Phase 57 engine)
    plan = await prep_svc.generate_real_preparation_plan(
        db, candidate["id"], str(body.job_id) if body.job_id else None
    )

    # Build a daily schedule recommendation
    top_items = plan["plan_items"][:min(len(plan["plan_items"]), days_until + 1)]

    daily_schedule = []
    for i, item in enumerate(top_items):
        day_offset = i
        target_date = now.replace() if day_offset == 0 else None
        daily_schedule.append({
            "day": day_offset + 1,
            "focus_domain": item["domain_code"],
            "reason": item["reason"],
            "priority_score": item["priority_score"],
        })

    return {
        "target_company": body.target_company,
        "target_role": body.target_role,
        "interview_date": body.interview_date.isoformat(),
        "days_until_interview": days_until,
        "current_readiness": readiness.get("overall"),
        "preparation_plan": {
            "top_domains": [i["domain_code"] for i in top_items[:5]],
            "daily_schedule": daily_schedule,
            "total_domains_to_cover": plan["total_domains_evaluated"],
        },
        "note": (
            "This plan is based on your real session history and job requirements. "
            "Scores are null until you complete practice sessions."
        ),
    }


@router.get("/interview-day/readiness-check")
async def interview_day_readiness_check(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Phase 82 — Interview-Day Mode: Last-mile readiness check.

    IMPORTANT: This is PRE-interview preparation practice.
    It is NOT real-time assistance during an employer's live interview.
    Providing hidden assistance in real interviews would be cheating —
    PRAXIS does not support that and never will.

    Returns:
    - Current readiness per dimension
    - Weakest areas to review in the next few hours
    - Key facts to remember per domain
    - Communication metrics summary
    """
    readiness = await r2_svc.get_readiness_v2(db, candidate["id"])

    # Identify 3 weakest dimensions for last-minute review
    dims = readiness.get("dimensions", {})
    sorted_dims = sorted(
        [(k, v) for k, v in dims.items() if v.get("score") is not None],
        key=lambda x: x[1]["score"]
    )
    weak_areas = sorted_dims[:3]

    # JD gaps if job provided
    jd_gaps = []
    if job_id:
        gap_rows = await db.execute(text("""
            SELECT g.requirement_text, g.importance
            FROM candidate_jd_evidence e
            JOIN jd_requirement_graph g ON g.id = e.requirement_id
            WHERE e.candidate_id = :cid AND g.job_id = :jid AND e.covered = FALSE
              AND g.importance = 'required'
            LIMIT 5
        """), {"cid": candidate["id"], "jid": str(job_id)})
        jd_gaps = [dict(r._mapping) for r in jd_rows.fetchall()] if False else []
        # Note: execute returns row directly
        jd_gaps = [dict(r._mapping) for r in gap_rows.fetchall()]

    return {
        "mode": "interview_day_preparation",
        "disclaimer": "This is pre-interview practice. PRAXIS does not provide assistance during real interviews.",
        "overall_readiness": readiness.get("overall"),
        "weak_areas_to_review": [
            {
                "domain": area[0],
                "score": area[1]["score"],
                "trend": area[1].get("trend"),
                "advice": f"Quick review: focus on the core concepts in {area[0]}.",
            }
            for area in weak_areas
        ],
        "uncovered_jd_requirements": jd_gaps,
        "preparation_complete": (
            readiness.get("overall") is not None
            and readiness["overall"].get("score", 0) >= 65
        ),
    }
