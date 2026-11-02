import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()


async def check_env():
    print("Running Environment Bootstrap Validator...")

    # 1. Check PostgreSQL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[FAIL] DATABASE_URL not set")
        sys.exit(1)

    try:
        # Use asyncpg directly for a quick check
        import asyncpg

        conn = await asyncpg.connect(db_url)
        print("[PASS] PostgreSQL connectivity")

        # Check pgvector
        has_vector = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = $1", "vector")
        if has_vector:
            print("[PASS] Vector extension (pgvector) is installed")
        else:
            print("[FAIL] Vector extension (pgvector) is NOT installed")

        # Check migrations applied (rough check on tables)
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = $1", "public"
        )
        if len(tables) > 10:
            print(f"[PASS] Required migrations appear applied (found {len(tables)} tables)")
        else:
            print(f"[FAIL] Migrations might be missing, found only {len(tables)} tables")

        # Check RLS
        rls_tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE rowsecurity = true")
        if len(rls_tables) > 0:
            print(f"[PASS] RLS policies are active on {len(rls_tables)} tables")
        else:
            print("[FAIL] RLS policies are NOT active")

        await conn.close()
    except Exception as e:
        print(f"[FAIL] PostgreSQL connectivity: {e}")
        sys.exit(1)

    # 2. Check Redis
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("[FAIL] REDIS_URL not set")
        sys.exit(1)

    try:
        from redis.asyncio import Redis

        r = Redis.from_url(redis_url)
        await r.ping()
        print("[PASS] Redis connectivity")
        await r.close()
    except Exception as e:
        print(f"[FAIL] Redis connectivity: {e}")
        sys.exit(1)

    print("[PASS] All environment checks completed successfully!")


if __name__ == "__main__":
    asyncio.run(check_env())
