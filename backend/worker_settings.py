import os
import asyncio
from arq.connections import RedisSettings
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# OpenTelemetry Setup
resource = Resource.create({"service.name": "praxis-worker"})
provider = TracerProvider(resource=resource)

# Export to Jaeger (from Phase 1.1 docker-compose, default port 4318 for OTLP HTTP)
otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Trivial Smoke-Test Job
async def ping_job(ctx, message: str) -> str:
    # TEMPORARY SMOKE TEST JOB - Delete/mark once Stage 2 adds real jobs
    with tracer.start_as_current_span("ping_job") as span:
        span.set_attribute("ping.message", message)
        await asyncio.sleep(0.1) # Simulate minimal work
        return f"pong: {message}"

# (Deleted inline delete_candidate_account_job to use the one from worker_tasks instead)

# Phase 1.13: Supabase Keepalive (Belt and Suspenders)
async def supabase_keepalive_job(ctx):
    """
    Runs every 24 hours. Connects to the database and performs a lightweight 
    query (e.g., SELECT 1) to prevent the Supabase Free Tier from pausing due 
    to 7 days of inactivity.
    """
    try:
        import httpx
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if url and key:
            # REST ping
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{url}/rest/v1/skills?limit=1", headers={"apikey": key, "Authorization": f"Bearer {key}"})
                r.raise_for_status()
                print("Keepalive successful.")
    except Exception as e:
        print(f"Keepalive failed: {e}")



REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

import arq

async def on_startup(ctx):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/praxis")
    ctx['db_engine'] = create_async_engine(db_url)
    
    # Initialize providers (simple init for health check)
    from praxis_ai_gateway.providers.ollama import OllamaProvider
    from praxis_ai_gateway.providers.groq import GroqProvider
    from praxis_ai_gateway.providers.openai import OpenAIProvider
    
    ctx['providers'] = {
        "ollama": OllamaProvider(),
        "groq": GroqProvider(),
        "openai": OpenAIProvider()
    }

async def on_shutdown(ctx):
    if 'db_engine' in ctx:
        await ctx['db_engine'].dispose()

# Note: arq expects a redis.asyncio.ConnectionPool style URL or RedisSettings.
# We parse out host and port for RedisSettings manually or pass the string if supported.
class WorkerSettings:
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    
    # Stage 2/3 will append real job functions here

    from praxis_ai_gateway.tasks import check_provider_health
    from backend.app.workers.document_worker import process_document
    from backend.app.workers.embedding_worker import generate_embeddings
    from backend.app.worker_tasks import analyze_job, cleanup_old_sessions, purge_expired_retention_data, delete_candidate_account_job, process_resume, generate_study_material_job

    
    functions = [
        # ping_job, # SMOKE TEST - Retained but not part of production registry
        delete_candidate_account_job,
        supabase_keepalive_job,
        check_provider_health,
        process_document,
        generate_embeddings,
        process_resume,
        analyze_job,
        cleanup_old_sessions,
        purge_expired_retention_data,
        generate_study_material_job
    ]
    
    # Register scheduled background jobs
    cron_jobs = [
        arq.cron(supabase_keepalive_job, hour=12, minute=0), # Runs daily at Noon
        arq.cron(check_provider_health, second={0}), # Every 60s
        arq.cron(cleanup_old_sessions, minute={0, 15, 30, 45}), # Every 15 mins
        arq.cron(purge_expired_retention_data, hour=3, minute=0) # Daily at 3 AM
    ]  
    
    max_jobs = 10
    
    # 5 minutes — generous for document processing; revisit once real embedding job durations are measured
    job_timeout = 300  
    
    retry_jobs = True
    max_tries = 3
    
    # Failure Visibility Convention Hook
    @staticmethod
    async def on_job_end(ctx, job_id, job_name, args, kwargs, result, was_cancelled, exception):
        if exception:
            job_try = ctx.get('job_try', 1)
            if job_try >= 3:
                try:
                    db = ctx.get('db_engine')
                    if db:
                        from sqlalchemy import text
                        import json
                        
                        candidate_id = kwargs.get('candidate_id')
                        if not candidate_id and len(args) > 1 and isinstance(args[1], str) and len(args[1]) > 20: # heuristic
                            pass # We might parse args if needed, but kwargs is safer if named
                            
                        # Dump args properly
                        args_json = json.dumps({"args": args, "kwargs": kwargs}, default=str)
                        
                        async with db.begin() as conn:
                            await conn.execute(text(
                                "INSERT INTO failed_jobs (job_name, job_id, args, error_message, candidate_id) VALUES (:name, :jid, :args, :err, :cid)"
                            ), {"name": job_name, "jid": job_id, "args": args_json, "err": str(exception), "cid": candidate_id})
                except Exception as e:
                    print(f"Failed to record dead letter job: {e}")
                print(f"[DEAD LETTER] Job {job_name} ({job_id}) failed permanently after {job_try} tries: {exception}")
