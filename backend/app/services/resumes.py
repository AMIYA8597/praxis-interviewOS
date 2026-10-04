"""
Resume upload & fact review.

Upload never parses inline: the file is validated, stored under a
candidate-scoped key, recorded as `documents`+`resumes` rows, and the
`process_resume` ARQ job does parse -> chunk -> embed -> extract.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.queue import enqueue
from backend.app.core.storage import ObjectStorage
from backend.app.core.uploads import validate_resume_upload
from backend.app.exceptions import NotFoundError, ServiceUnavailableError
from backend.app.repositories import resumes as repo
from backend.app.repositories.base import Page
from backend.app.schemas.resume import (
    ResumeFactResponse,
    ResumeResponse,
    ResumeStatusResponse,
    ResumeUploadResponse,
)

logger = logging.getLogger(__name__)


def storage_key(candidate_id: str, document_id: uuid.UUID, safe_filename: str) -> str:
    # Per-candidate isolation: every object lives under the owner's id.
    return f"{candidate_id}/resumes/{document_id}/{safe_filename}"


async def upload_resume(
    db: AsyncSession,
    storage: ObjectStorage,
    arq_pool,
    *,
    candidate_id: str,
    file: UploadFile,
    max_bytes: int,
) -> ResumeUploadResponse:
    upload = await validate_resume_upload(file, max_bytes)
    document_id = uuid.uuid4()
    key = storage_key(candidate_id, document_id, upload.safe_filename)

    try:
        await storage.put(key, upload.data, upload.mime_type)
    except Exception as e:
        logger.error("resume_storage_failed", extra={"error_type": type(e).__name__})
        raise ServiceUnavailableError("File storage is temporarily unavailable")

    try:
        _, resume = await repo.create_document_and_resume(
            db,
            candidate_id=candidate_id,
            document_id=document_id,
            original_filename=upload.safe_filename,
            storage_path=key,
            mime_type=upload.mime_type,
            size_bytes=upload.size,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await storage.delete(key)  # don't leave orphaned blobs
        except Exception:
            logger.warning("resume_blob_cleanup_failed")
        raise

    logger.info(
        "resume_uploaded",
        extra={"document_id": str(document_id), "size_bytes": upload.size, "mime_type": upload.mime_type},
    )

    queued = await enqueue(arq_pool, "process_resume", str(document_id), job_id=f"process_resume:{document_id}")
    if not queued:
        await repo.set_document_status(db, document_id, "failed", "Processing queue unavailable; please re-upload")
        await db.commit()
        raise ServiceUnavailableError("Resume stored but processing could not be scheduled; please retry")

    return ResumeUploadResponse(
        id=resume.id,
        document_id=document_id,
        status="uploading",
        processing_status="uploading",
        message="Resume accepted for processing",
    )


async def _require_owned(db: AsyncSession, resume_id, candidate_id):
    found = await repo.get_owned_with_document(db, resume_id, candidate_id)
    if found is None:
        raise NotFoundError("Resume")
    return found


def _to_response(resume, document) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        candidate_id=resume.candidate_id,
        document_id=resume.document_id,
        filename=document.original_filename if document else None,
        mime_type=document.mime_type if document else None,
        size_bytes=document.size_bytes if document else None,
        is_primary=bool(resume.is_primary),
        processing_status=document.processing_status if document else None,
        error_message=document.error_message if document else None,
        created_at=resume.created_at,
    )


async def list_resumes(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    page = await repo.list_owned(db, candidate_id, cursor=cursor, limit=limit)
    docs = await repo.documents_for(db, {r.document_id for r in page.items})
    return Page(items=[_to_response(r, docs.get(r.document_id)) for r in page.items], next_cursor=page.next_cursor)


async def get_resume(db: AsyncSession, resume_id, candidate_id: str) -> ResumeResponse:
    resume, document = await _require_owned(db, resume_id, candidate_id)
    return _to_response(resume, document)


async def get_status(db: AsyncSession, resume_id, candidate_id: str) -> ResumeStatusResponse:
    resume, document = await _require_owned(db, resume_id, candidate_id)
    return ResumeStatusResponse(
        id=resume.id, processing_status=document.processing_status, error_message=document.error_message
    )


async def list_facts(db: AsyncSession, resume_id, candidate_id: str) -> List[ResumeFactResponse]:
    await _require_owned(db, resume_id, candidate_id)
    return [ResumeFactResponse.from_claim(c) for c in await repo.list_claims(db, resume_id, candidate_id)]


async def _require_fact(db, resume_id, fact_id, candidate_id):
    claim = await repo.get_claim(db, resume_id, fact_id, candidate_id)
    if claim is None:
        raise NotFoundError("Fact")
    return claim


async def confirm_fact(db: AsyncSession, resume_id, fact_id, candidate_id: str) -> ResumeFactResponse:
    claim = await _require_fact(db, resume_id, fact_id, candidate_id)
    claim.verified_by_user = True
    claim.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(claim)
    return ResumeFactResponse.from_claim(claim)


async def update_fact(db: AsyncSession, resume_id, fact_id, candidate_id: str, content: str) -> ResumeFactResponse:
    claim = await _require_fact(db, resume_id, fact_id, candidate_id)
    claim.claim_text = content
    claim.verified_by_user = True
    claim.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(claim)
    return ResumeFactResponse.from_claim(claim)


async def reject_fact(db: AsyncSession, resume_id, fact_id, candidate_id: str) -> None:
    claim = await _require_fact(db, resume_id, fact_id, candidate_id)
    await repo.delete_claim(db, claim)
    await db.commit()
