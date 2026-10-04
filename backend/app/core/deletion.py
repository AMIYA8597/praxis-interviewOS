import logging
from typing import Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

# Candidate-owned tables, counted before the cascade for the audit summary.
_COUNTED = (
    ("documents", "SELECT count(*) FROM documents WHERE candidate_id = CAST(:cid AS uuid)"),
    ("practice_sessions", "SELECT count(*) FROM practice_sessions WHERE candidate_id = CAST(:cid AS uuid)"),
    ("candidate_projects", "SELECT count(*) FROM candidate_projects WHERE candidate_id = CAST(:cid AS uuid)"),
    ("jobs", "SELECT count(*) FROM jobs WHERE candidate_id = CAST(:cid AS uuid)"),
    ("study_items", "SELECT count(*) FROM study_items WHERE candidate_id = CAST(:cid AS uuid)"),
    ("applications", "SELECT count(*) FROM applications WHERE candidate_id = CAST(:cid AS uuid)"),
)


class DeletionService:
    """
    "Delete everything" for a candidate.

    1. Record storage keys (blobs live outside the DB).
    2. Detach cross-candidate references (session_claims.source_chunk_id).
    3. DELETE the candidate row; FK ON DELETE CASCADE removes documents,
       chunks, resumes, sessions, turns, scores, jobs, study items, ...
    4. Purge profile-scoped personal data (usage, notifications, BYO keys).
    5. Delete blobs (best effort; failures are logged and reported).
    """

    def __init__(self, db: AsyncEngine, storage_client=None):
        self.db = db
        self.storage_client = storage_client

    async def process_deletion_job(self, candidate_id: str) -> Dict:
        logger.info("deletion_started", extra={"candidate_id": candidate_id})
        summary: Dict = {}
        async with self.db.begin() as conn:
            for name, q in _COUNTED:
                summary[name] = (await conn.execute(text(q), {"cid": candidate_id})).scalar() or 0

            profile_row = (
                await conn.execute(
                    text("SELECT profile_id FROM candidates WHERE id = CAST(:cid AS uuid)"), {"cid": candidate_id}
                )
            ).first()
            profile_id = str(profile_row[0]) if profile_row else None

            res = await conn.execute(
                text("SELECT storage_path FROM documents WHERE candidate_id = CAST(:cid AS uuid) AND storage_path IS NOT NULL"),
                {"cid": candidate_id},
            )
            storage_paths = [r[0] for r in res.fetchall()]
            res = await conn.execute(
                text("SELECT storage_path FROM screenshot_tasks WHERE candidate_id = CAST(:cid AS uuid)"),
                {"cid": candidate_id},
            )
            storage_paths += [r[0] for r in res.fetchall() if r[0]]

            await conn.execute(
                text("""
                    UPDATE session_claims SET source_chunk_id = NULL
                    WHERE source_chunk_id IN (
                        SELECT dc.id FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.candidate_id = CAST(:cid AS uuid)
                    )
                """),
                {"cid": candidate_id},
            )
            deleted = await conn.execute(text("DELETE FROM candidates WHERE id = CAST(:cid AS uuid)"), {"cid": candidate_id})
            summary["candidates"] = deleted.rowcount

            if profile_id:
                # Fixed allow-list of table names (not user input).
                for table in ("usage_events", "notifications", "shortcuts", "provider_configs"):
                    r = await conn.execute(
                        text(f"DELETE FROM {table} WHERE profile_id = CAST(:pid AS uuid)"), {"pid": profile_id}
                    )
                    summary[table] = r.rowcount
                await conn.execute(
                    text("UPDATE model_requests SET prompt = NULL, response = NULL WHERE profile_id = CAST(:pid AS uuid)"),
                    {"pid": profile_id},
                )

        failed_blobs = 0
        if self.storage_client and storage_paths:
            for path in storage_paths:
                try:
                    await self.storage_client.delete(path)
                except Exception as e:
                    failed_blobs += 1
                    logger.error("deletion_blob_failed", extra={"error_type": type(e).__name__})
        summary["storage_objects"] = len(storage_paths)
        summary["storage_objects_failed"] = failed_blobs
        logger.info("deletion_completed", extra={"candidate_id": candidate_id, "summary": summary})
        return summary
