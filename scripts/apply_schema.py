import asyncio
import asyncpg
import re

async def run():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    with open(r'd:\work\interviewOS\supabase\migrations\20260907235800_init_core_schema.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
        
    # Remove triggers and functions that might fail or are not needed for this test
    # Actually, asyncpg.execute can run multiple statements.
    try:
        await conn.execute(sql)
        print("Core schema initialized.")
    except Exception as e:
        print("Failed:", e)
        
    with open(r'd:\work\interviewOS\supabase\migrations\20260907235801_add_vector_indexes.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    try:
        await conn.execute(sql)
        print("Vector indexes initialized.")
    except Exception as e:
        print("Failed indexes:", e)
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
