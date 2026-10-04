"""Reconcile the Alembic chain with the canonical schema.

Revision ID: 004_reconcile_schema
Revises: 003_full_data_model_and_rls
Create Date: 2026-10-04

Background
----------
Revisions 001-003 created an early prototype schema (candidate_profiles,
projects, interview_sessions, ...) that diverged from the schema the
application, RLS policies and CI actually use: supabase/migrations/*.sql
(applied by scripts/migrate.py). backend/app/db/models.py mirrors the latter.

What this revision does
-----------------------
1. If prototype tables from 001-003 exist, they are *renamed* to
   `legacy_<name>` (indexes and PK/unique constraints too, because index
   names are schema-global). No data is dropped; migrate rows manually and
   drop the legacy tables when satisfied.
2. Applies every supabase/migrations/*.sql file not yet recorded in
   `schema_migrations` (shared with scripts/migrate.py, so running both
   tools is safe), degrading vector(384) to text when pgvector is absent.

Databases already built with scripts/migrate.py must NOT run 001-003 (their
tables would collide). Adopt Alembic there with
`alembic stamp 004_reconcile_schema`, then keep using either tool.

Downgrade is intentionally unsupported (it would require dropping the
canonical schema and its data).
"""
import os
import sys
from typing import Sequence, Union

from alembic import op

revision: str = "004_reconcile_schema"
down_revision: Union[str, None] = "003_full_data_model_and_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every table created by revisions 001-003.
LEGACY_TABLES = [
    "candidate_profiles", "resumes", "document_chunks", "jobs", "jd_requirements", "skills",
    "candidate_skills", "projects", "metrics", "stories", "experiences", "interview_sessions",
    "questions", "answers", "claims", "rubric_scores", "resume_claims", "session_turns",
    "turn_metrics", "turn_scores", "session_claims", "study_items", "study_reviews",
    "provider_health", "usage_events",
]

_RENAME_LEGACY = """
DO $$
DECLARE
  t text;
  r record;
  legacy_tables text[] := %(tables)s;
BEGIN
  -- Only act on a database that actually holds the 001-003 prototype schema.
  IF to_regclass('public.candidate_profiles') IS NULL THEN
    RETURN;
  END IF;
  FOREACH t IN ARRAY legacy_tables LOOP
    IF to_regclass('public.' || t) IS NULL THEN
      CONTINUE;
    END IF;
    -- PK/unique constraints (renaming the constraint renames its index).
    FOR r IN
      SELECT conname FROM pg_constraint
      WHERE conrelid = ('public.' || t)::regclass AND contype IN ('p', 'u')
    LOOP
      EXECUTE format('ALTER TABLE public.%%I RENAME CONSTRAINT %%I TO %%I',
                     t, r.conname, left('legacy_' || r.conname, 63));
    END LOOP;
    -- Remaining standalone indexes.
    FOR r IN
      SELECT indexname FROM pg_indexes
      WHERE schemaname = 'public' AND tablename = t AND indexname NOT LIKE 'legacy\\_%%'
    LOOP
      EXECUTE format('ALTER INDEX public.%%I RENAME TO %%I', r.indexname, left('legacy_' || r.indexname, 63));
    END LOOP;
    EXECUTE format('ALTER TABLE public.%%I RENAME TO %%I', t, 'legacy_' || t);
    RAISE NOTICE 'renamed prototype table %% to legacy_%%', t, t;
  END LOOP;
END $$;
"""


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def upgrade() -> None:
    bind = op.get_bind()
    raw = bind.connection.driver_connection  # psycopg2 connection (inside Alembic's transaction)

    def exec_sql(sql: str) -> None:
        with raw.cursor() as cur:
            cur.execute(sql)  # no params => no %-interpolation of the SQL text

    array_literal = "ARRAY[" + ",".join(f"'{t}'" for t in LEGACY_TABLES) + "]::text[]"
    exec_sql(_RENAME_LEGACY % {"tables": array_literal})

    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.migrate import apply_sync

    def fetch_versions():
        with raw.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations")
            return [row[0] for row in cur.fetchall()]

    def record(version: str) -> None:
        with raw.cursor() as cur:
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))

    with raw.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        has_vector = cur.fetchone() is not None

    apply_sync(exec_sql, fetch_versions, record, has_vector, log=lambda m: print(f"[004_reconcile_schema] {m}"))


def downgrade() -> None:
    raise NotImplementedError(
        "004_reconcile_schema is not reversible: it adopts the canonical schema. "
        "Restore from backup instead; prototype data remains in legacy_* tables."
    )
