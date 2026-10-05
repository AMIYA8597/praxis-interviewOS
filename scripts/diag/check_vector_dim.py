import asyncio
import os
import uuid
import random
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis@localhost:5432/praxis")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        try:
            # 128 dim vector
            bad_vec = [random.random() for _ in range(128)]
            q = text("""
                INSERT INTO document_chunks (id, content, embedding)
                VALUES (:id, 'test', :emb)
            """)
            await conn.execute(q, {"id": str(uuid.uuid4()), "emb": str(bad_vec)})
            print("INSERT SUCCEEDED (UNEXPECTED)")
        except Exception as e:
            print("INSERT REJECTED AS EXPECTED:")
            print(e)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
