-- ============
-- FAILED JOBS REPORTING
-- ============
-- This table implements the Dead Letter / Failure Visibility convention for arq.
-- When a background job (e.g., document parsing, embedding generation) exhausts 
-- all its retries (max_tries = 3), the worker process is responsible for writing 
-- a record here. 
-- 
-- Stage 2/3 will implement the actual `on_job_end` hook in arq to populate this.

create table if not exists failed_jobs (
  id uuid primary key default gen_random_uuid(),
  job_name text not null,
  job_id text not null,
  args jsonb,
  error_message text,
  failed_at timestamptz not null default now(),
  candidate_id uuid references candidates(id) on delete set null, -- Nullable, as some jobs are system-wide
  resolved boolean not null default false
);

alter table failed_jobs enable row level security;

-- Only admins can see failed jobs
create policy "failed_jobs_select_admin" 
on failed_jobs for select 
using (
  exists (select 1 from admin_users where profile_id = auth.uid())
);

-- Service role will insert them from the worker. 
