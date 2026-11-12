from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from backend.app.dependencies import get_db_session, get_redis, get_ai_gateway

router = APIRouter(tags=["health"])

@router.get("/health", status_code=status.HTTP_200_OK)
@router.get("/health/live", status_code=status.HTTP_200_OK)
async def live_check():
    """Liveness probe. Always returns 200 OK if the process is up."""
    return {"status": "ok"}

@router.get("/health/db-tables", status_code=status.HTTP_200_OK)
async def db_tables_check(db: AsyncSession = Depends(get_db_session)):
    """Diagnostic: list tables and check key columns exist."""
    try:
        res = await db.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('public', 'auth') ORDER BY table_schema, table_name"
        ))
        tables = [{"schema": r[0], "table": r[1]} for r in res.fetchall()]
    except Exception as e:
        return {"error": f"tables query failed: {e}"}

    try:
        res2 = await db.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'profiles' AND table_schema = 'public'"
        ))
        profile_cols = [{"column": r[0], "type": r[1]} for r in res2.fetchall()]
    except Exception as e:
        profile_cols = [{"error": str(e)}]

    try:
        res3 = await db.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'candidates' AND table_schema = 'public'"
        ))
        candidate_cols = [{"column": r[0], "type": r[1]} for r in res3.fetchall()]
    except Exception as e:
        candidate_cols = [{"error": str(e)}]

    return {
        "tables": tables,
        "profile_columns": profile_cols,
        "candidate_columns": candidate_cols,
    }

@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def ready_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """Readiness probe. Checks DB and Redis connectivity."""
    db_ok = False
    db_reason = None
    redis_ok = False
    redis_reason = None

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_reason = str(e)

    try:
        await redis.ping()
        redis_ok = True
    except Exception as e:
        redis_reason = str(e)

    if db_ok and redis_ok:
        return {"status": "ready"}
    
    # If anything failed, return 503
    payload = {
        "status": "not_ready",
        "components": {}
    }
    
    if not db_ok:
        payload["components"]["database"] = {"status": "fail", "reason": db_reason}
    if not redis_ok:
        payload["components"]["redis"] = {"status": "fail", "reason": redis_reason}

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)

@router.get("/health/startup", status_code=status.HTTP_200_OK)
async def startup_check(db: AsyncSession = Depends(get_db_session)):
    """Startup probe. Checks DB connectivity and verifies all migrations are current."""
    try:
        from scripts.migrate import migration_files
        all_files = migration_files()
        expected = {f.name for f in all_files}
    except Exception:
        import pathlib
        mig_dir = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "supabase" / "migrations"
        expected = {f.name for f in mig_dir.glob("*.sql")}

    try:
        res = await db.execute(text("SELECT version FROM schema_migrations"))
        applied = {row[0] for row in res.fetchall()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "reason": f"schema_migrations unqueryable: {e}"},
        )

    pending = expected - applied
    if pending:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "reason": "Pending database migrations",
                "pending_count": len(pending),
                "pending": sorted(list(pending)),
            },
        )

    return {
        "status": "ready",
        "migrations_current": True,
        "applied_count": len(applied),
        "total_migrations": len(expected),
    }

@router.get("/health/providers", status_code=status.HTTP_200_OK)
async def providers_check(gateway = Depends(get_ai_gateway)):
    """AI Providers readiness snapshot."""
    providers_status = {}
    from praxis_ai_gateway.resilience import CircuitBreaker
    
    health_results = await gateway.check_provider_health() if hasattr(gateway, "check_provider_health") else {}
    for name, provider in gateway.providers.items():
        caps = provider.capabilities()
        cb = CircuitBreaker(gateway.redis, gateway.db, name, "generate")
        state = await cb.get_state()
        
        providers_status[name] = {
            "capabilities": caps.model_dump(),
            "circuit_breaker_state": state,
            "healthy": health_results.get(name, False),
        }
        
    return {"status": "ok", "providers": providers_status}
