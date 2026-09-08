import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from redis.asyncio import Redis

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
import os

resource = Resource.create({"service.name": "praxis-core-api"})
provider = TracerProvider(resource=resource)
otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
trace.set_tracer_provider(provider)

from packages.config.settings import Settings
from backend.app.middleware import RequestIdMiddleware
from backend.app.exceptions import global_exception_handler

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.candidates import router as candidates_router
from backend.app.api.resumes import router as resumes_router
from backend.app.api.projects import router as projects_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.study import router as study_router
from backend.app.api.outreach import router as outreach_router
from backend.app.api.applications import router as applications_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.admin import router as admin_router

from contextvars import ContextVar
import logging

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True

# Configure logging format to include request_id
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [req_id=%(request_id)s] - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.addFilter(RequestIdFilter())

logger = logging.getLogger("praxis.backend")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(handler)

# Ensure the root logger also uses it if needed, but for now we attach to our namespace
logging.getLogger("uvicorn").addFilter(RequestIdFilter())

def create_app() -> FastAPI:
    settings = Settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), echo=False)
        app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
        
        redis_pool = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        app.state.redis_pool = redis_pool
        
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        app.state.tracer_provider = provider
        
        from backend.app.dependencies import AIGatewayStub, ObjectStorageStub
        app.state.ai_gateway = AIGatewayStub()
        app.state.object_storage = ObjectStorageStub()
        
        logger.info(
            "backend_ready: db=connected, redis=connected, telemetry=initialized, env=%s",
            settings.APP_ENV
        )
        yield
        
        # Shutdown
        await engine.dispose()
        await redis_pool.close()

    docs_url = "/docs" if settings.APP_ENV != "production" else None
    redoc_url = "/redoc" if settings.APP_ENV != "production" else None
    openapi_url = "/openapi.json" if settings.APP_ENV != "production" else None

    app = FastAPI(
        title="PRAXIS Backend API",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url
    )

    from backend.app.rate_limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)

    api_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(candidates_router, prefix=api_prefix)
    app.include_router(resumes_router, prefix=api_prefix)
    app.include_router(projects_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(sessions_router, prefix=api_prefix)
    app.include_router(study_router, prefix=api_prefix)
    app.include_router(outreach_router, prefix=api_prefix)
    app.include_router(applications_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)
    
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)

    return app

app = create_app()
