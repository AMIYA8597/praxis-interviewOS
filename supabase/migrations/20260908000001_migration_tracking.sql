-- ============
-- MIGRATION STATUS TRACKING
-- ============
-- Records per-migration timing and outcome. Written by scripts/migrate.py via
-- log_migration(). schema_migrations remains the source of truth for "has this
-- file been applied"; migration_status is the audit/timing log.
--
-- This file is fully idempotent: scripts/migrate.py executes it as a bootstrap
-- step before applying any migration, so timing is captured for every file
-- (including those that sort before this one).

create table if not exists migration_status (
  id serial primary key,
  version text not null,
  name text not null,
  applied_at timestamptz default now(),
  execution_time_ms int,
  status text check (status in ('success', 'failed', 'rolled_back'))
);

-- Two migration files may share a timestamp prefix (e.g. 20260918000000_*),
-- so uniqueness must be on (version, name), not version alone. Replace the
-- original single-column constraint if an older copy of this table exists.
do $$
begin
  if exists (
    select 1 from pg_constraint
    where conrelid = 'public.migration_status'::regclass
      and conname = 'migration_status_version_key'
  ) then
    alter table migration_status drop constraint migration_status_version_key;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.migration_status'::regclass
      and conname = 'migration_status_version_name_key'
  ) then
    alter table migration_status
      add constraint migration_status_version_name_key unique (version, name);
  end if;
end $$;

-- RLS on, no policies: invisible to anon/authenticated clients. The migration
-- runner connects as the table owner and is unaffected.
alter table migration_status enable row level security;

create or replace function log_migration(p_version text, p_name text, p_time_ms int, p_status text)
returns void as $$
begin
  insert into migration_status (version, name, execution_time_ms, status)
  values (p_version, p_name, p_time_ms, p_status)
  on conflict (version, name) do update
  set status = excluded.status,
      applied_at = now(),
      execution_time_ms = excluded.execution_time_ms;
end;
$$ language plpgsql;

-- Supabase exposes public functions over PostgREST RPC; clients must not be
-- able to write to the migration log.
revoke execute on function log_migration(text, text, int, text) from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke execute on function log_migration(text, text, int, text) from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke execute on function log_migration(text, text, int, text) from authenticated;
  end if;
end $$;
