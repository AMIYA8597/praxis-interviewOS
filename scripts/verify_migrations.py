"""
Migration consistency check (needs a Postgres server; creates and drops
throwaway databases next to DATABASE_URL's database).

1. canonical: scripts/migrate.py on an empty DB
2. alembic:   001..003 (prototype) + seeded legacy row, then 004 -> head
3. asserts both produce the same public tables/columns, that every ORM
   model column exists, and that the legacy row was preserved.

    python scripts/verify_migrations.py [--keep]
"""
import argparse
import asyncio
import os
import sys

import asyncpg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "packages", "ai-gateway")]

from packages.config.settings import settings  # noqa: E402

BASE = settings.sync_database_url.rsplit("/", 1)[0]
CANON, ALEMBIC = "praxis_verify_canonical", "praxis_verify_alembic"


async def _recreate(name: str) -> None:
    c = await asyncpg.connect(f"{BASE}/postgres")
    try:
        await c.execute(f'DROP DATABASE IF EXISTS "{name}"')
        await c.execute(f'CREATE DATABASE "{name}"')
    finally:
        await c.close()


async def _drop(name: str) -> None:
    c = await asyncpg.connect(f"{BASE}/postgres")
    try:
        await c.execute(f'DROP DATABASE IF EXISTS "{name}"')
    finally:
        await c.close()


async def _columns(name: str) -> dict:
    c = await asyncpg.connect(f"{BASE}/{name}")
    try:
        rows = await c.fetch(
            "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'"
        )
    finally:
        await c.close()
    out: dict = {}
    for r in rows:
        out.setdefault(r["table_name"], set()).add(r["column_name"])
    return out


def _alembic(url: str, target: str) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(ROOT, "backend", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "backend", "alembic"))
    cfg.cmd_opts = argparse.Namespace(x=[f"db_url={url}"])
    command.upgrade(cfg, target)


async def main(keep: bool) -> int:
    from scripts.migrate import run_migrations
    from backend.app.db.models import Base

    failures = []
    await _recreate(CANON)
    await run_migrations(f"{BASE}/{CANON}")

    await _recreate(ALEMBIC)
    await asyncio.to_thread(_alembic, f"{BASE}/{ALEMBIC}", "003_full_data_model_and_rls")
    c = await asyncpg.connect(f"{BASE}/{ALEMBIC}")
    await c.execute(
        "INSERT INTO candidate_profiles (id, user_id, name) VALUES (gen_random_uuid(), gen_random_uuid(), 'legacy row')"
    )
    await c.close()
    await asyncio.to_thread(_alembic, f"{BASE}/{ALEMBIC}", "head")

    canon, alem = await _columns(CANON), await _columns(ALEMBIC)
    alem_current = {t: cols for t, cols in alem.items() if not t.startswith("legacy_") and t != "alembic_version"}
    if set(canon) != set(alem_current):
        failures.append(f"table sets differ: {sorted(set(canon) ^ set(alem_current))}")
    for t in set(canon) & set(alem_current):
        if canon[t] != alem_current[t]:
            failures.append(f"{t}: column diff {sorted(canon[t] ^ alem_current[t])}")
    for table in Base.metadata.sorted_tables:
        missing = {c.name for c in table.columns} - canon.get(table.name, set())
        if missing:
            failures.append(f"model {table.name} has columns missing in DB: {sorted(missing)}")

    c = await asyncpg.connect(f"{BASE}/{ALEMBIC}")
    legacy = await c.fetchval("SELECT count(*) FROM legacy_candidate_profiles")
    head = await c.fetchval("SELECT version_num FROM alembic_version")
    await c.close()
    if legacy != 1:
        failures.append(f"legacy data not preserved (rows={legacy})")
    if head != "004_reconcile_schema":
        failures.append(f"unexpected alembic head {head}")

    if not keep:
        await _drop(CANON)
        await _drop(ALEMBIC)
    for f in failures:
        print("FAIL:", f)
    print(f"tables={len(canon)} legacy_tables={len([t for t in alem if t.startswith('legacy_')])} "
          f"alembic_head={head} -> {'OK' if not failures else 'FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--keep", action="store_true")
    sys.exit(asyncio.run(main(p.parse_args().keep)))
