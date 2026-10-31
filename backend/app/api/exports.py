"""
GDPR/CCPA-style candidate data self-export.

POST /api/v1/export         — enqueue an export job; returns the export record ID
GET  /api/v1/export/{id}    — poll status; returns signed download URL when ready
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_arq_pool, get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES

router = APIRouter(tags=["exports"], responses=COMMON_ERROR_RESPONSES)


class ExportInitiated(BaseModel):
    export_id: str
    status: str
    requested_at: datetime
    message: str


class ExportStatus(BaseModel):
    export_id: str
    status: str
    requested_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    download_url: str | None = None


@router.post(
    "/export",
    response_model=ExportInitiated,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a full data export",
    description=(
        "Initiates an asynchronous export of all personal data for the authenticated candidate "
        "(sessions, scores, projects, experiences, skills, STAR stories, resumes, analytics). "
        "The export is processed in the background; poll GET /api/v1/export/{id} for status. "
        "A signed download URL is returned when the export is ready. Exports expire after 24 hours."
    ),
)
async def initiate_export(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    arq_pool=Depends(get_arq_pool),
):
    # Rate-limit: one pending/processing export at a time per candidate.
    existing = await db.execute(
        text("""
            SELECT id FROM candidate_data_exports
            WHERE candidate_id = :cid
              AND status IN ('pending', 'processing')
            LIMIT 1
        """),
        {"cid": candidate["id"]},
    )
    if existing.mappings().first():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="An export is already in progress. Please wait for it to complete.",
        )

    row = await db.execute(
        text("""
            INSERT INTO candidate_data_exports (candidate_id, status)
            VALUES (:cid, 'pending')
            RETURNING id, requested_at
        """),
        {"cid": candidate["id"]},
    )
    await db.commit()
    record = row.mappings().first()
    export_id = str(record["id"])

    if arq_pool is not None:
        await arq_pool.enqueue_job(
            "run_data_export",
            export_id,
            candidate["id"],
            _job_id=f"export:{export_id}",
        )

    return ExportInitiated(
        export_id=export_id,
        status="pending",
        requested_at=record["requested_at"],
        message="Export queued. Poll GET /api/v1/export/{export_id} to check status.",
    )


@router.get(
    "/export/{export_id}",
    response_model=ExportStatus,
    summary="Get data export status",
    description=(
        "Returns the current status of an export job. "
        "When status is 'ready', a signed download_url is included (valid for 24 hours). "
        "When status is 'expired' the download_url is no longer accessible."
    ),
)
async def get_export_status(
    export_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    row = await db.execute(
        text("""
            SELECT id, status, requested_at, completed_at, expires_at, download_url
            FROM candidate_data_exports
            WHERE id = :eid AND candidate_id = :cid
        """),
        {"eid": str(export_id), "cid": candidate["id"]},
    )
    record = row.mappings().first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    # Auto-expire: if URL TTL passed, update status.
    if (
        record["status"] == "ready"
        and record["expires_at"] is not None
        and record["expires_at"] < datetime.now(timezone.utc)
    ):
        await db.execute(
            text("UPDATE candidate_data_exports SET status='expired' WHERE id=:eid"),
            {"eid": str(export_id)},
        )
        await db.commit()
        return ExportStatus(
            export_id=str(export_id),
            status="expired",
            requested_at=record["requested_at"],
            completed_at=record["completed_at"],
            expires_at=record["expires_at"],
            download_url=None,
        )

    return ExportStatus(
        export_id=str(record["id"]),
        status=record["status"],
        requested_at=record["requested_at"],
        completed_at=record.get("completed_at"),
        expires_at=record.get("expires_at"),
        download_url=record.get("download_url"),
    )
