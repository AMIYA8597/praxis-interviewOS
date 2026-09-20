import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/postgres')
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE study_items ADD COLUMN IF NOT EXISTS repetitions int default 0;'))
    await engine.dispose()
asyncio.run(main())
