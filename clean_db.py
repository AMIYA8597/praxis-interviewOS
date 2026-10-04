import asyncio, asyncpg
async def run():
    try:
        from packages.config.settings import settings
        conn = await asyncpg.connect(settings.DATABASE_URL)
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        # Drop mock auth if exists
        await conn.execute("DROP SCHEMA IF EXISTS auth CASCADE;")
        await conn.execute("DROP SCHEMA IF EXISTS storage CASCADE;")
        await conn.close()
        print('DB clean ok')
    except Exception as e:
        print(e)
asyncio.run(run())
