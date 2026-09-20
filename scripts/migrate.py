import asyncio
import asyncpg
import os
import pathlib
import sys
import re

# Standard local docker-compose credentials if not provided by env
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://praxis:dev_password@localhost:5432/praxis")

async def run_migrations():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Create migrations tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version text PRIMARY KEY,
                applied_at timestamp with time zone DEFAULT now()
            )
        """)
        
        base_dir = pathlib.Path(__file__).parent.parent
        migrations_dir = base_dir / 'supabase' / 'migrations'
        
        # Get all .sql files, sorted by filename
        sql_files = sorted([f for f in migrations_dir.iterdir() if f.suffix == '.sql'])
        
        if not sql_files:
            print(f"No migrations found in {migrations_dir}")
            return
            
        applied_versions = {row['version'] for row in await conn.fetch("SELECT version FROM schema_migrations")}
        
        # Check if vector extension is available
        has_vector = False
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            has_vector = True
        except Exception:
            pass
        
        for sql_file in sql_files:
            version = sql_file.name
            
            if version in applied_versions:
                print(f"Skipping {version} (already applied)")
                continue
                
            print(f"Applying {version}...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql = f.read().lstrip('\ufeff')
            
            # If vector isn't available, downgrade it so it doesn't break
            if not has_vector:
                sql = re.sub(r"using hnsw\s*\([^)]+\)", "(embedding)", sql, flags=re.IGNORECASE)
                sql = re.sub(r"with\s*\([^)]*m\s*=\s*\d+[^)]*\)", "", sql, flags=re.IGNORECASE)
                sql = sql.replace("create extension if not exists vector;", "")
                sql = sql.replace("vector(384)", "text")
                sql = sql.replace("vector_cosine_ops", "")
            
            # Start a transaction for each file
            async with conn.transaction():
                # Execute the migration
                await conn.execute(sql)
                # Record it
                await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)
                
            print(f"Successfully applied {version}")
            
    except Exception as e:
        print(f"Migration failed! Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await conn.close()
        
    print("All migrations applied successfully.")

if __name__ == '__main__':
    asyncio.run(run_migrations())
