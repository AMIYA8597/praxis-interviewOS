"""
Apply supabase/migrations/*.sql in filename order, tracking applied files in
`schema_migrations` and timing data in `migration_status`.

    python scripts/migrate.py [--database-url postgresql://...]

Public API (used by Alembic revision 004 and the test suite):
    apply_async(conn, log=print) -> int
    apply_sync(exec_sql, fetch_versions, record, has_vector, log=print) -> int
"""
import argparse
import asyncio
import pathlib
import re
import sys
import time
from typing import Callable, Iterable, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"

# Idempotent migration that defines migration_status + log_migration(). It is
# executed as a bootstrap step before the main loop so that timing is recorded
# for every migration, including those that sort before it.
TRACKING_MIGRATION = "20260908000001_migration_tracking.sql"

TRACKING_DDL = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version text PRIMARY KEY,
        applied_at timestamp with time zone DEFAULT now()
    )
"""


def migration_files(directory: pathlib.Path = MIGRATIONS_DIR) -> List[pathlib.Path]:
    return sorted(f for f in directory.iterdir() if f.suffix == ".sql")


def split_migration_name(filename: str) -> Tuple[str, str]:
    """'20260908000001_migration_tracking.sql' -> ('20260908000001', 'migration_tracking')."""
    stem = pathlib.Path(filename).stem
    version, _, name = stem.partition("_")
    return version, name or stem


def adapt_sql(sql: str, has_vector: bool) -> str:
    """Strip BOM and, without pgvector, degrade vector DDL to text."""
    sql = sql.lstrip("﻿")
    if not has_vector:
        sql = re.sub(r"using hnsw\s*\([^)]+\)", "(embedding)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"with\s*\([^)]*m\s*=\s*\d+[^)]*\)", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"create extension if not exists vector;?", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"vector\(\d+\)", "text", sql, flags=re.IGNORECASE)
        sql = sql.replace("vector_cosine_ops", "")
    return sql


def pending(applied: Iterable[str], files: List[pathlib.Path]) -> List[Tuple[str, pathlib.Path]]:
    done = set(applied)
    return [(f.name, f) for f in files if f.name not in done]


async def _log_migration_async(conn, filename: str, elapsed_ms: int, status: str) -> None:
    """Record timing/outcome in migration_status. Never masks the migration's own error."""
    version, name = split_migration_name(filename)
    try:
        await conn.execute(
            "SELECT log_migration($1, $2, $3, $4)", version, name, elapsed_ms, status
        )
    except Exception as e:
        print(
            f"Warning: could not record {status} status for {filename} in migration_status: {e}",
            file=sys.stderr,
        )


async def apply_async(conn, log: Callable[[str], None] = print) -> int:
    """Apply pending migrations on an asyncpg connection. Returns the number applied."""
    await conn.execute(TRACKING_DDL)

    # Bootstrap migration_status / log_migration() before the main loop so that
    # timing is recorded for every migration, including those that sort before it.
    tracking_file = MIGRATIONS_DIR / TRACKING_MIGRATION
    if tracking_file.exists():
        async with conn.transaction():
            await conn.execute(adapt_sql(tracking_file.read_text(encoding="utf-8"), True))

    applied = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}

    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        has_vector = True
    except Exception:
        has_vector = False
        log("pgvector not available: embedding columns fall back to text")

    count = 0
    for version, path in pending(applied, migration_files()):
        log(f"Applying {version}...")
        sql = adapt_sql(path.read_text(encoding="utf-8"), has_vector)
        start = time.monotonic()
        try:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)", version
                )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            await _log_migration_async(conn, version, elapsed_ms, "failed")
            raise RuntimeError(f"Migration {version} failed after {elapsed_ms} ms") from e
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await _log_migration_async(conn, version, elapsed_ms, "success")
        log(f"  done ({elapsed_ms} ms)")
        count += 1
    return count


def apply_sync(
    exec_sql: Callable[[str], None],
    fetch_versions: Callable[[], Iterable[str]],
    record: Callable[[str], None],
    has_vector: bool,
    log: Callable[[str], None] = print,
) -> int:
    """Apply pending migrations via a synchronous connection (used by Alembic)."""
    exec_sql(TRACKING_DDL)
    count = 0
    for version, path in pending(fetch_versions(), migration_files()):
        log(f"Applying {version}...")
        exec_sql(adapt_sql(path.read_text(encoding="utf-8"), has_vector))
        record(version)
        count += 1
    return count


async def run_migrations(database_url: str) -> None:
    import asyncpg

    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to database: {url.split('@')[-1]}")
    try:
        conn = await asyncpg.connect(url)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        n = await apply_async(conn)
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await conn.close()
    print(f"All migrations applied successfully ({n} new).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    url = args.database_url
    if not url:
        sys.path.insert(0, str(ROOT))
        from packages.config.settings import settings
        url = settings.DATABASE_URL
    asyncio.run(run_migrations(url))


if __name__ == "__main__":
    main()
