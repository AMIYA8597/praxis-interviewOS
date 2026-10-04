from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import CandidateProject
from backend.app.exceptions import NotFoundError
from backend.app.repositories import owned
from backend.app.repositories.base import Page
from backend.app.schemas.project import ProjectCreate, ProjectUpdate


def _to_columns(data: Dict[str, Any]) -> Dict[str, Any]:
    if "business_value" in data:
        data["business_impact"] = data.pop("business_value")
    return data


async def create_project(db: AsyncSession, candidate_id: str, payload: ProjectCreate) -> CandidateProject:
    values = _to_columns(payload.model_dump())
    # Entered by the user themself, so it counts as verified.
    values["verified_by_user"] = True
    project = await owned.create_owned(db, CandidateProject, candidate_id, values)
    await db.commit()
    return project


async def list_projects(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    return await owned.list_owned(db, CandidateProject, candidate_id, cursor=cursor, limit=limit)


async def get_project(db: AsyncSession, project_id, candidate_id: str) -> CandidateProject:
    project = await owned.get_owned(db, CandidateProject, project_id, candidate_id)
    if project is None:
        raise NotFoundError("Project")
    return project


async def update_project(db: AsyncSession, project_id, candidate_id: str, payload: ProjectUpdate) -> CandidateProject:
    values = _to_columns(payload.model_dump(exclude_unset=True))
    project = await owned.update_owned(db, CandidateProject, project_id, candidate_id, values)
    if project is None:
        raise NotFoundError("Project")
    await db.commit()
    return project


async def delete_project(db: AsyncSession, project_id, candidate_id: str) -> None:
    if not await owned.delete_owned(db, CandidateProject, project_id, candidate_id):
        raise NotFoundError("Project")
    await db.commit()
