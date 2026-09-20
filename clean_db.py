import asyncio, asyncpg, sys
async def run():
    try:
        conn = await asyncpg.connect('postgresql://praxis:dev_password@localhost:5432/praxis')
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        # Drop mock auth if exists
        await conn.execute("DROP SCHEMA IF EXISTS auth CASCADE;")
        await conn.execute("DROP SCHEMA IF EXISTS storage CASCADE;")
        await conn.close()
        print('DB clean ok')
    except Exception as e:
        print(e)
asyncio.run(run())
