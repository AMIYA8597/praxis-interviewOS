import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
    rows = await conn.fetch('SELECT datname FROM pg_database;')
    for r in rows:
        print(r['datname'])
    await conn.close()
asyncio.run(main())
