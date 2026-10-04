import asyncio, asyncpg
async def main():
    from packages.config.settings import settings
    conn = await asyncpg.connect(settings.DATABASE_URL)
    rows = await conn.fetch('SELECT datname FROM pg_database;')
    for r in rows:
        print(r['datname'])
    await conn.close()
asyncio.run(main())
