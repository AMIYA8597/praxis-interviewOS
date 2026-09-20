-- ============
-- MIGRATION STATUS TRACKING
-- ============

create table if not exists migration_status (
  id serial primary key,
  version text not null unique,
  name text not null,
  applied_at timestamptz default now(),
  execution_time_ms int,
  status text check (status in ('success', 'failed', 'rolled_back'))
);

create or replace function log_migration(p_version text, p_name text, p_time_ms int, p_status text)
returns void as $$
begin
  insert into migration_status (version, name, execution_time_ms, status)
  values (p_version, p_name, p_time_ms, p_status)
  on conflict (version) do update 
  set status = EXCLUDED.status, 
      applied_at = now(),
      execution_time_ms = EXCLUDED.execution_time_ms;
end;
$$ language plpgsql;
