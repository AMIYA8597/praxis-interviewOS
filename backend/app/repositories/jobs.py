from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import JobBlueprint, JobMatch, JobRequirement
from backend.app.repositories.base import as_uuid


async def get_blueprint(db: AsyncSession, job_id) -> Optional[JobBlueprint]:
    stmt = select(JobBlueprint).where(JobBlueprint.job_id == as_uuid(job_id))
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_requirements(db: AsyncSession, blueprint_id) -> List[JobRequirement]:
    stmt = (
        select(JobRequirement)
        .where(JobRequirement.job_blueprint_id == as_uuid(blueprint_id))
        .order_by(JobRequirement.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_match(db: AsyncSession, job_id, candidate_id) -> Optional[JobMatch]:
    stmt = select(JobMatch).where(JobMatch.job_id == as_uuid(job_id), JobMatch.candidate_id == as_uuid(candidate_id))
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_match(
    db: AsyncSession,
    job_id,
    candidate_id,
    overall_score: Optional[float],
    methodology_version: str,
    breakdown: Optional[dict | list],
) -> JobMatch:
    stmt = select(JobMatch).where(JobMatch.job_id == as_uuid(job_id), JobMatch.candidate_id == as_uuid(candidate_id))
    match = (await db.execute(stmt)).scalar_one_or_none()
    if match is None:
        match = JobMatch(
            job_id=as_uuid(job_id),
            candidate_id=as_uuid(candidate_id),
            overall_score=overall_score,
            methodology_version=methodology_version,
            breakdown=breakdown,
        )
        db.add(match)
    else:
        match.overall_score = overall_score
        match.methodology_version = methodology_version
        match.breakdown = breakdown
    await db.flush()
    return match
