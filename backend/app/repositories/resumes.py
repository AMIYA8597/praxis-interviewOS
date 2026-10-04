from typing import List, Optional, Tuple

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document, Resume, ResumeClaim, ResumeVersion
from backend.app.repositories.base import Page, as_uuid, paginate


async def create_document_and_resume(
    db: AsyncSession,
    *,
    candidate_id: str,
    document_id,
    original_filename: str,
    storage_path: str,
    mime_type: str,
    size_bytes: int,
) -> Tuple[Document, Resume]:
    doc = Document(
        id=document_id,
        candidate_id=as_uuid(candidate_id),
        kind="resume",
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        processing_status="uploading",
    )
    db.add(doc)
    await db.flush()
    resume = Resume(candidate_id=as_uuid(candidate_id), document_id=doc.id, is_primary=False)
    db.add(resume)
    await db.flush()
    return doc, resume


async def set_document_status(db: AsyncSession, document_id, status: str, error: Optional[str] = None) -> None:
    await db.execute(
        update(Document)
        .where(Document.id == as_uuid(document_id))
        .values(processing_status=status, error_message=error)
    )


async def get_owned_with_document(db: AsyncSession, resume_id, candidate_id) -> Optional[Tuple[Resume, Document]]:
    if as_uuid(resume_id) is None:
        return None
    stmt = (
        select(Resume, Document)
        .join(Document, Document.id == Resume.document_id)
        .where(Resume.id == as_uuid(resume_id), Resume.candidate_id == as_uuid(candidate_id))
    )
    row = (await db.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def list_owned(db: AsyncSession, candidate_id, *, cursor: Optional[str], limit: int) -> Page:
    stmt = select(Resume).where(Resume.candidate_id == as_uuid(candidate_id))
    return await paginate(db, stmt, Resume, cursor=cursor, limit=limit)


async def documents_for(db: AsyncSession, document_ids) -> dict:
    if not document_ids:
        return {}
    rows = (await db.execute(select(Document).where(Document.id.in_(list(document_ids))))).scalars().all()
    return {d.id: d for d in rows}


def _claims_for_resume_stmt(resume_id, candidate_id):
    return (
        select(ResumeClaim)
        .join(ResumeVersion, ResumeVersion.id == ResumeClaim.resume_version_id)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(Resume.id == as_uuid(resume_id), Resume.candidate_id == as_uuid(candidate_id))
    )


async def list_claims(db: AsyncSession, resume_id, candidate_id) -> List[ResumeClaim]:
    stmt = _claims_for_resume_stmt(resume_id, candidate_id).order_by(ResumeClaim.created_at.asc(), ResumeClaim.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def get_claim(db: AsyncSession, resume_id, claim_id, candidate_id) -> Optional[ResumeClaim]:
    if as_uuid(claim_id) is None or as_uuid(resume_id) is None:
        return None
    stmt = _claims_for_resume_stmt(resume_id, candidate_id).where(ResumeClaim.id == as_uuid(claim_id))
    return (await db.execute(stmt)).scalar_one_or_none()


async def delete_claim(db: AsyncSession, claim: ResumeClaim) -> None:
    await db.execute(delete(ResumeClaim).where(ResumeClaim.id == claim.id))
