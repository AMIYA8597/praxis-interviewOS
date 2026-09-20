import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/postgres')
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE solver_results ADD COLUMN IF NOT EXISTS screenshot_type text;'))
        await conn.execute(text('ALTER TABLE solver_results ADD COLUMN IF NOT EXISTS hints jsonb;'))
        await conn.execute(text('ALTER TABLE study_items DROP CONSTRAINT IF EXISTS study_items_source_check;'))
        await conn.execute(text("ALTER TABLE study_items ADD CONSTRAINT study_items_source_check CHECK (source in ('weak_answer','missed_concept','jd_gap','manual','screenshot_solve'));"))
        await conn.execute(text('ALTER TABLE study_items ADD COLUMN IF NOT EXISTS solver_result_id uuid REFERENCES solver_results(id) ON DELETE CASCADE;'))
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
