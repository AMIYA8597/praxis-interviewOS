import os
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

async def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_settings = RedisSettings.from_dsn(redis_url)
    
    print("Connecting to Redis queue...")
    pool = await create_pool(redis_settings)
    
    print("Enqueueing ping_job...")
    job = await pool.enqueue_job('ping_job', 'hello')
    
    if not job:
        print("Failed to enqueue job.")
        return
        
    print(f"Job {job.job_id} enqueued. Waiting for result...")
    try:
        # Wait for the job to finish (with a timeout)
        result = await job.info()
        result = await job.result(timeout=5)
        print(f"Job Result: {result}")
        if result == "pong: hello":
            print("SUCCESS! Smoke test round-tripped perfectly.")
        else:
            print("FAILED: Unexpected result.")
    except asyncio.TimeoutError:
        print("FAILED: Job result timed out. Is the worker process running? (Run scripts/worker-up.ps1 in another terminal)")
    except Exception as e:
        print(f"FAILED with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
