-- ============
-- DATA LIFECYCLE EXTENSIONS
-- ============

-- 1. Extend user_settings for Retention Policy Enforcement
alter table user_settings 
add column if not exists data_retention_days int default 30;

-- 2. Extend deletion_jobs to match the async deletion worker contract
-- The initial schema included a basic deletion_jobs table. We need to 
-- ensure it holds the full audit contract requested by Phase 1.12.
alter table deletion_jobs
add column if not exists error_message text,
add column if not exists rows_deleted_summary jsonb;

-- Adjust candidate reference if needed. The init schema used profile_id.
-- For candidate-level purges, tracking by candidate_id is requested.
-- We can add candidate_id for granular candidate wipes.
alter table deletion_jobs
add column if not exists candidate_id uuid references candidates(id) on delete set null;

-- ============
-- DELETION JOBS RLS POLICIES
-- ============
alter table deletion_jobs enable row level security;

-- Only the owner can insert or view their own deletion jobs
create policy "Users can view own deletion jobs"
on deletion_jobs for select
using ( profile_id = auth.uid() );

create policy "Users can insert own deletion jobs"
on deletion_jobs for insert
with check ( profile_id = auth.uid() );

-- The service role (worker) handles updates
