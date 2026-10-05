"""
Phase 107 — Worker Reliability: Idempotency Keys.

Every irreversible worker operation (billing events, session finalization,
study card generation, deletion) must check an idempotency key before
executing.

Pattern:
    async with idempotent_job(db, job_id, "study_card_generate") as should_run:
        if should_run:
            await _do_work(...)

This ensures that if a job is retried after a partial failure, the
irreversible effect is not duplicated.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _check_idempotency(db: AsyncSession, idempotency_key: str) -> Optional[str]:
    """Return the existing status for this key, or None if first execution."""
    row = await db.execute(text("""
        SELECT status FROM worker_idempotency_log WHERE idempotency_key = :key
    """), {"key": idempotency_key})
    result = row.fetchone()
    return result[0] if result else None


async def _mark_started(db: AsyncSession, idempotency_key: str, job_type: str) -> None:
    await db.execute(text("""
        INSERT INTO worker_idempotency_log (idempotency_key, job_type, status, started_at)
        VALUES (:key, :job_type, 'started', :now)
        ON CONFLICT (idempotency_key) DO NOTHING
    """), {"key": idempotency_key, "job_type": job_type, "now": datetime.now(timezone.utc).isoformat()})
    await db.commit()


async def _mark_completed(db: AsyncSession, idempotency_key: str) -> None:
    await db.execute(text("""
        UPDATE worker_idempotency_log
        SET status = 'completed', finished_at = :now
        WHERE idempotency_key = :key
    """), {"key": idempotency_key, "now": datetime.now(timezone.utc).isoformat()})
    await db.commit()


async def _mark_failed(db: AsyncSession, idempotency_key: str, error: str) -> None:
    await db.execute(text("""
        UPDATE worker_idempotency_log
        SET status = 'failed', finished_at = :now, error = :error
        WHERE idempotency_key = :key
    """), {"key": idempotency_key, "now": datetime.now(timezone.utc).isoformat(), "error": error[:500]})
    await db.commit()


@asynccontextmanager
async def idempotent_job(db: AsyncSession, idempotency_key: str, job_type: str):
    """
    Context manager that enforces idempotency.

    Yields True if the job should execute (first time or after a failed attempt).
    Yields False if the job was already completed successfully (skip).
    """
    existing = await _check_idempotency(db, idempotency_key)

    if existing == "completed":
        logger.info("worker_job_already_completed", extra={"key": idempotency_key, "type": job_type})
        yield False
        return

    if existing == "started":
        # Previous run started but didn't complete — may be a retry after crash.
        # Allow re-execution (the operation must be designed to handle this).
        logger.info("worker_job_restarting", extra={"key": idempotency_key, "type": job_type})

    await _mark_started(db, idempotency_key, job_type)

    try:
        yield True
        await _mark_completed(db, idempotency_key)
        logger.info("worker_job_completed", extra={"key": idempotency_key, "type": job_type})
    except Exception as e:
        await _mark_failed(db, idempotency_key, str(e))
        logger.error("worker_job_failed", extra={"key": idempotency_key, "type": job_type, "error": str(e)})
        raise
