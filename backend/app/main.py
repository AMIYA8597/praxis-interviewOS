import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from backend.app.api.admin import router as admin_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.applications import router as applications_router
from backend.app.api.auth import router as auth_router
from backend.app.api.candidates import router as candidates_router
from backend.app.api.health import router as health_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.outreach import router as outreach_router
from backend.app.api.projects import router as projects_router
from backend.app.api.resumes import router as resumes_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.study import router as study_router
from backend.app.api.questions import router as questions_router
from backend.app.core.bootstrap import build_gateway, configure_logging, configure_tracing
from backend.app.core.context import request_id_context  # noqa: F401  (re-exported for older imports)
from backend.app.core.queue import create_arq_pool
from backend.app.db.session import create_engine, create_session_factory
from backend.app.exceptions import register_exception_handlers
from backend.app.middleware import RequestIdMiddleware
from packages.config.settings import Settings

logger = logging.getLogger("praxis.backend")


def create_app(cfg: Settings | None = None) -> FastAPI:
    settings = cfg or Settings()
    configure_logging(settings, "praxis-core-api")
    configure_tracing(settings, "praxis-core-api")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(settings)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)

        redis_pool = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT_S,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_S,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL_S,
        )
        app.state.redis_pool = redis_pool
        app.state.arq_pool = await create_arq_pool(settings.REDIS_URL)

        from backend.app.core.storage import get_storage_client

        app.state.object_storage = get_storage_client()
        app.state.ai_gateway = build_gateway(settings, redis_pool, app.state.db_session_factory)

        logger.info(
            "backend_ready",
            extra={
                "app_env": settings.APP_ENV,
                "queue": "connected" if app.state.arq_pool else "unavailable",
                "auth_dev_bypass": settings.auth_dev_bypass_enabled,
                "providers": sorted(app.state.ai_gateway.providers),
            },
        )
        if settings.auth_dev_bypass_enabled:
            logger.warning("auth_dev_bypass_enabled: every bearer token maps to AUTH_DEV_USER_ID (development only)")
        try:
            yield
        finally:
            if app.state.arq_pool is not None:
                try:
                    await app.state.arq_pool.aclose()
                except Exception:
                    pass
            await redis_pool.aclose()
            await engine.dispose()
            logger.info("backend_stopped")

    docs_enabled = settings.api_docs_enabled
    app = FastAPI(
        title="PRAXIS Backend API",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        debug=False,
    )

    from backend.app.rate_limiter import RateLimitMiddleware

    # Order: last added = outermost. RequestId must wrap everything so even
    # rate-limited/CORS-rejected responses carry an id and get logged.
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS and "*" not in settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    api_prefix = "/api/v1"
    for r in (
        health_router,
        auth_router,
        candidates_router,
        resumes_router,
        projects_router,
        jobs_router,
        sessions_router,
        study_router,
        questions_router,
        outreach_router,
        applications_router,
        analytics_router,
        admin_router,
    ):
        app.include_router(r, prefix=api_prefix)

    if settings.otel_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
