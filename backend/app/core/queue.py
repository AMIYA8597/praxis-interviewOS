"""Thin wrapper around ARQ enqueueing with trace propagation and logging."""
import logging
from typing import Any, Optional

from opentelemetry.propagate import inject

logger = logging.getLogger(__name__)


async def create_arq_pool(redis_url: str):
    """Create the ARQ pool or return None (API keeps serving; jobs are reported as not queued)."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        rs = RedisSettings.from_dsn(redis_url)
        rs.conn_retries = 0  # fail fast at API startup; enqueue() then reports unavailability
        rs.conn_timeout = 2
        return await create_pool(rs)
    except Exception as e:
        logger.warning("arq_pool_unavailable", extra={"error_type": type(e).__name__})
        return None


async def enqueue(arq_pool, job_name: str, *args: Any, job_id: Optional[str] = None, **kwargs: Any) -> bool:
    """Enqueue `job_name`; returns False (never raises) if the queue is unavailable."""
    if arq_pool is None:
        logger.error("job_not_enqueued", extra={"job_name": job_name, "reason": "queue_unavailable"})
        return False
    carrier: dict = {}
    inject(carrier)
    try:
        job = await arq_pool.enqueue_job(job_name, *args, trace_carrier=carrier, _job_id=job_id, **kwargs)
    except Exception as e:
        logger.error("job_enqueue_failed", extra={"job_name": job_name, "error_type": type(e).__name__})
        return False
    # arq returns None when a job with the same _job_id is already queued.
    logger.info("job_enqueued", extra={"job_name": job_name, "job_id": getattr(job, "job_id", job_id)})
    return True
