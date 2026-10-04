"""
ARQ worker entrypoint:  arq backend.worker_settings.WorkerSettings

Retry / dead-letter policy: each job is wrapped by
`backend.app.worker_tasks.job`, which retries transient failures with
exponential backoff (5s, 10s, ...) up to WORKER_MAX_TRIES and records the
final failure in `failed_jobs`.
"""
import logging

import arq
from arq.connections import RedisSettings
from redis.asyncio import Redis

from backend.app.core.bootstrap import build_gateway, build_providers, configure_logging, configure_tracing
from backend.app.db.session import create_engine, create_session_factory
from backend.app.worker_tasks import (
    analyze_job,
    cleanup_old_sessions,
    delete_candidate_account_job,
    generate_session_debrief_job,
    generate_study_material_job,
    process_resume,
    purge_expired_retention_data,
)
from backend.app.workers.document_worker import process_document
from backend.app.workers.embedding_worker import generate_embeddings
from packages.config.settings import settings
from praxis_ai_gateway.tasks import check_provider_health

logger = logging.getLogger("praxis.worker")

configure_logging(settings, "praxis-worker")
configure_tracing(settings, "praxis-worker")

# Backwards-compatible module constant (older code imported it).
REDIS_URL = settings.REDIS_URL


async def supabase_keepalive_job(ctx):
    """Daily lightweight query so a free-tier Supabase project is not paused for inactivity."""
    try:
        from sqlalchemy import text

        async with ctx["db_engine"].connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("keepalive_ok")
    except Exception as e:
        logger.warning("keepalive_failed", extra={"error_type": type(e).__name__})


async def on_startup(ctx):
    engine = create_engine(settings)
    ctx["db_engine"] = engine
    ctx["db_session_factory"] = create_session_factory(engine)
    
    # Cross-tenant operations need a superuser connection to bypass RLS.
    admin_url = settings.async_database_url.replace("praxis_app:app_password", "postgres:postgres")
    if admin_url != settings.async_database_url:
        admin_engine = create_engine(settings, url=admin_url)
    else:
        admin_engine = engine
    ctx["admin_db_engine"] = admin_engine
    
    ctx["redis"] = Redis.from_url(settings.REDIS_URL, decode_responses=True, max_connections=settings.REDIS_MAX_CONNECTIONS)
    ctx["providers"] = build_providers()
    ctx["gateway"] = build_gateway(settings, ctx["redis"], ctx["db_session_factory"], providers=ctx["providers"])
    from backend.app.core.storage import get_storage_client

    ctx["storage"] = get_storage_client()
    logger.info("worker_ready", extra={"providers": sorted(ctx["providers"])})


async def on_shutdown(ctx):
    if ctx.get("redis") is not None:
        await ctx["redis"].aclose()
    if ctx.get("db_engine") is not None:
        await ctx["db_engine"].dispose()
    if ctx.get("admin_db_engine") is not None and ctx.get("admin_db_engine") is not ctx.get("db_engine"):
        await ctx.get("admin_db_engine").dispose()
    logger.info("worker_stopped")


class WorkerSettings:
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = settings.ARQ_QUEUE_NAME

    functions = [
        process_resume,
        process_document,
        generate_embeddings,
        analyze_job,
        generate_session_debrief_job,
        delete_candidate_account_job,
        generate_study_material_job,
        cleanup_old_sessions,
        purge_expired_retention_data,
        supabase_keepalive_job,
        check_provider_health,
    ]

    cron_jobs = [
        arq.cron(supabase_keepalive_job, hour=12, minute=0),
        arq.cron(check_provider_health, second={0}),
        arq.cron(cleanup_old_sessions, minute={0, 15, 30, 45}),
        arq.cron(purge_expired_retention_data, hour=3, minute=0),
    ]

    max_jobs = settings.WORKER_MAX_JOBS
    job_timeout = settings.WORKER_JOB_TIMEOUT_S
    retry_jobs = True
    # One more than the wrapper's limit so the wrapper (not arq) decides the final failure.
    max_tries = settings.WORKER_MAX_TRIES + 1
    keep_result = 3600
