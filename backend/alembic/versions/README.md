# Alembic Migrations Retired

`backend/alembic/versions` has been retired.
`supabase/migrations/*.sql` is the sole canonical source of schema DDL and migrations across all environments (local development, CI, staging, and production).

All database schema changes must be authored as SQL files in `supabase/migrations/` and applied via `npx supabase db reset` or `python scripts/migrate.py`.
