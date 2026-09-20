import asyncio, asyncpg, sys
async def run():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
        await conn.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'praxis') THEN
                    CREATE ROLE praxis WITH LOGIN SUPERUSER PASSWORD 'dev_password';
                ELSE
                    ALTER ROLE praxis SUPERUSER;
                END IF;
            END $$;
        """)
        
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'praxis'")
        if not db_exists:
            pass
        await conn.close()

        if not db_exists:
            conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
            await conn.execute("CREATE DATABASE praxis OWNER praxis")
            await conn.close()
            
        print('DB setup ok')
    except Exception as e:
        print(e)
asyncio.run(run())
