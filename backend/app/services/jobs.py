from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.queue import enqueue
from backend.app.db.models import Job
from backend.app.exceptions import NotFoundError
from backend.app.repositories import jobs as jobs_repo
from backend.app.repositories import owned
from backend.app.repositories.base import Page
from backend.app.schemas.job import (
    JobAcceptedResponse,
    JobBlueprintResponse,
    JobCreate,
    JobDetailResponse,
    JobMatchResponse,
    JobRequirementResponse,
    JobResponse,
)


async def create_job(db: AsyncSession, arq_pool, candidate_id: str, payload: JobCreate) -> JobAcceptedResponse:
    job = await owned.create_owned(
        db,
        Job,
        candidate_id,
        {
            "company_name": payload.company,
            "role_title": payload.role_title,
            "raw_jd_text": payload.description,
            "processing_status": "pending",
        },
    )
    await db.commit()
    queued = await enqueue(arq_pool, "analyze_job", str(job.id), job_id=f"analyze_job:{job.id}")
    if not queued:
        job.processing_status = "failed"
        job.error_message = "Analysis queue unavailable; please retry"
        await db.commit()
        return JobAcceptedResponse(id=job.id, status="failed", message="Job saved but analysis could not be scheduled")
    return JobAcceptedResponse(id=job.id, status="pending", message="Job accepted for analysis")


async def list_jobs(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    page = await owned.list_owned(db, Job, candidate_id, cursor=cursor, limit=limit)
    return Page(items=[JobResponse.model_validate(j) for j in page.items], next_cursor=page.next_cursor)


async def get_job(db: AsyncSession, job_id, candidate_id: str) -> JobDetailResponse:
    job = await owned.get_owned(db, Job, job_id, candidate_id)
    if job is None:
        raise NotFoundError("Job")
    base = JobResponse.model_validate(job).model_dump()
    blueprints = []
    bp = await jobs_repo.get_blueprint(db, job.id)
    if bp is not None:
        reqs = await jobs_repo.list_requirements(db, bp.id)
        blueprints.append(
            JobBlueprintResponse(
                id=bp.id,
                summary=bp.summary,
                top_skills=bp.top_skills,
                likely_topics=list(bp.likely_topics or []),
                prep_pack=bp.prep_pack,
                requirements=[JobRequirementResponse.model_validate(r) for r in reqs],
            )
        )
    matches = []
    match = await jobs_repo.get_match(db, job.id, candidate_id)
    if match is not None:
        matches.append(
            JobMatchResponse(
                id=match.id,
                overall_score=float(match.overall_score) if match.overall_score is not None else None,
                methodology_version=match.methodology_version,
                breakdown=match.breakdown,
            )
        )
    return JobDetailResponse(**base, raw_jd_text=job.raw_jd_text, blueprints=blueprints, matches=matches)


async def delete_job(db: AsyncSession, job_id, candidate_id: str) -> None:
    if not await owned.delete_owned(db, Job, job_id, candidate_id):
        raise NotFoundError("Job")
    await db.commit()
