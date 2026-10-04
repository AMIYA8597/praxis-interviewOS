import logging
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DeletionService:
    """
    Manages the 'Delete Everything' cascade logic, ensuring that
    resumes, chunks, and decoupled dependencies are cleaned up safely
    without dangling FKs or relying purely on SQL cascading.

    This service never reads or writes deletion_jobs. The ARQ wrapper
    delete_candidate_account_job (backend/app/worker_tasks.py) is the single
    source of truth for deletion_jobs status transitions.
    """

    def __init__(self, db: AsyncEngine, storage_client=None):
        self.db = db
        self.storage_client = storage_client

    async def process_deletion_job(self, candidate_id: str):
        """
        Runs the deletion cascade for a candidate. Raises on failure so the
        caller can mark the deletion job as failed.
        """
        logger.info(f"Starting deletion cascade for candidate {candidate_id}")

        try:
            async with self.db.begin() as conn:
                # 1. Nullify source_chunk_ids in session_claims to avoid constraint errors
                # if we delete chunks first.
                await conn.execute(text("""
                    UPDATE session_claims SET source_chunk_id = NULL
                    WHERE source_chunk_id IN (
                        SELECT dc.id FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.candidate_id = :cid
                    )
                """), {"cid": candidate_id})

                # 2. Get storage paths for physical deletion before deleting db records
                res = await conn.execute(text("""
                    SELECT storage_path FROM documents WHERE candidate_id = :cid AND storage_path IS NOT NULL
                """), {"cid": candidate_id})
                storage_paths = [r[0] for r in res.fetchall()]

                # 3. Standard SQL Cascade takes care of the rest when we delete the candidate
                await conn.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})

                # deletion_jobs status is updated by the outer job wrapper in worker_tasks.py

            # 4. Purge physical storage blobs
            if self.storage_client and storage_paths:
                for path in storage_paths:
                    try:
                        await self.storage_client.delete(path)
                    except Exception as e:
                        logger.error(f"Failed to delete storage path {path}: {e}")

            logger.info(f"Deletion cascade completed for candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Deletion cascade failed for candidate {candidate_id}: {e}")
            raise
