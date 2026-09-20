from fastapi import APIRouter, Depends
from typing import Dict, Any
from backend.app.dependencies import get_current_user, get_current_candidate, get_redis
from redis.asyncio import Redis

router = APIRouter(tags=["auth"])

@router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user_id": user.get("sub"), "email": user.get("email")}

@router.delete("/auth/account")
async def delete_account(
    candidate: dict = Depends(get_current_candidate),
    redis: Redis = Depends(get_redis)
):
    import uuid
    from backend.worker_settings import WorkerSettings
    
    deletion_job_id = str(uuid.uuid4())
    # Enqueue arq task
    try:
        pool = await redis.pipeline()
        # Mocking arq enqueue logic. In reality we'd use ArqRedis.
        from arq import create_pool
        from backend.worker_settings import REDIS_URL
        from arq.connections import RedisSettings
        
        arq_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
        await arq_pool.enqueue_job("delete_candidate_account_job", deletion_job_id, candidate["id"])
    except Exception as e:
        import logging
        logging.error(f"Failed to enqueue account deletion: {e}")
        return {"status": "error", "message": str(e)}

    return {"status": "queued", "job_id": deletion_job_id}
