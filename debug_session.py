import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={'check_same_thread': False}, poolclass=StaticPool)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.connect() as conn:
        await conn.execute(text("CREATE TABLE candidates (id TEXT, profile_id TEXT, full_name TEXT)"))
        await conn.execute(text("CREATE TABLE practice_sessions (id TEXT, candidate_id TEXT, job_id TEXT, status TEXT)"))
        await conn.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES ('70733de4-b0e3-46f6-b9c5-0bf25dde6f75', '00000000-0000-0000-0000-000000000000', 'Test Candidate')"))
        await conn.execute(text("INSERT INTO practice_sessions (id, candidate_id, job_id) VALUES ('f2b48ce0-1668-42a4-aea5-0aca2954901f', '70733de4-b0e3-46f6-b9c5-0bf25dde6f75', 'd1c9ef0d-9b51-41b9-a9a7-9e0c52eb9b8a')"))
        await conn.commit()
        
    async with factory() as db:
        row = (await db.execute(text("""
            SELECT s.id, s.status, s.candidate_id
            FROM practice_sessions s
            JOIN candidates c ON s.candidate_id = c.id
            WHERE s.id = :sid AND c.profile_id = :uid
        """), {"sid": "f2b48ce0-1668-42a4-aea5-0aca2954901f", "uid": "00000000-0000-0000-0000-000000000000"})).first()
        print(f"Row: {row}")

asyncio.run(main())
