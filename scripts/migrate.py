import asyncio
import asyncpg
import pathlib
import sys
import re
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from packages.config.settings import settings

DATABASE_URL = settings.DATABASE_URL

# Idempotent migration that defines migration_status + log_migration(). It is
# executed as a bootstrap step before the main loop so that timing is recorded
# for every migration, including those that sort before it.
TRACKING_MIGRATION = '20260908000001_migration_tracking.sql'


def split_migration_name(filename: str) -> tuple[str, str]:
    """'20260908000001_migration_tracking.sql' -> ('20260908000001', 'migration_tracking')."""
    stem = pathlib.Path(filename).stem
    version, _, name = stem.partition('_')
    return version, name or stem


async def log_migration(conn, filename: str, elapsed_ms: int, status: str) -> None:
    """Record timing/outcome in migration_status. Never masks the migration's own result."""
    version, name = split_migration_name(filename)
    try:
        await conn.execute("SELECT log_migration($1, $2, $3, $4)", version, name, elapsed_ms, status)
    except Exception as e:
        print(f"Warning: could not record {status} status for {filename} in migration_status: {e}", file=sys.stderr)


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

        # Bootstrap migration_status / log_migration() (idempotent). This also
        # repairs databases where schema_migrations already lists the tracking
        # file but the objects themselves are missing.
        tracking_file = migrations_dir / TRACKING_MIGRATION
        if tracking_file.exists():
            async with conn.transaction():
                await conn.execute(tracking_file.read_text(encoding='utf-8').lstrip('\ufeff'))

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

            start = time.monotonic()
            try:
                # Start a transaction for each file
                async with conn.transaction():
                    # Execute the migration
                    await conn.execute(sql)
                    # Record it in schema_migrations (source of truth for "applied")
                    await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)
            except Exception as e:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                # The migration's transaction has rolled back; log the failure
                # outside it so the record survives, then abort the run.
                await log_migration(conn, version, elapsed_ms, 'failed')
                print(f"Migration {version} failed after {elapsed_ms} ms! Error: {e}", file=sys.stderr)
                sys.exit(1)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            await log_migration(conn, version, elapsed_ms, 'success')
            print(f"Successfully applied {version} ({elapsed_ms} ms)")

    except Exception as e:
        print(f"Migration failed! Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await conn.close()

    print("All migrations applied successfully.")

if __name__ == '__main__':
    asyncio.run(run_migrations())
