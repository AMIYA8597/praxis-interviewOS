from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from backend.app.dependencies import get_db_session, get_redis, get_ai_gateway

router = APIRouter(tags=["health"])

@router.get("/health/live", status_code=status.HTTP_200_OK)
async def live_check():
    """Liveness probe. Always returns 200 OK if the process is up."""
    return {"status": "ok"}

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

@router.get("/health/providers", status_code=status.HTTP_200_OK)
async def providers_check(gateway = Depends(get_ai_gateway)):
    """AI Providers readiness snapshot."""
    return {"status": getattr(gateway, "status", "not yet configured")}
