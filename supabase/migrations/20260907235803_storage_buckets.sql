-- ============
-- STORAGE BUCKETS
-- ============
-- We insert these directly into the Supabase storage schema.
-- Note: In a raw pgvector local docker without the Supabase Storage API, this migration
-- might fail if `storage` schema doesn't exist. We will safely create a mock schema for local dev.

create schema if not exists storage;

-- Mock tables if they don't exist (e.g. raw local postgres)
create table if not exists storage.buckets (
  id text primary key,
  name text not null,
  owner uuid,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  public boolean default false,
  file_size_limit bigint,
  allowed_mime_types text[]
);

create table if not exists storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets(id),
  name text,
  owner uuid,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  last_accessed_at timestamptz default now(),
  metadata jsonb
);

-- Insert buckets
insert into storage.buckets (id, name, public, file_size_limit)
values 
  ('resumes', 'resumes', false, 5242880),
  ('documents', 'documents', false, 5242880),
  ('screenshots', 'screenshots', false, 5242880),
  ('exports', 'exports', false, 5242880)
on conflict (id) do update set file_size_limit = EXCLUDED.file_size_limit;

-- ============
-- STORAGE RLS POLICIES
-- ============
alter table storage.objects enable row level security;

-- A user can only access objects if the object name starts with their candidate_id.
-- Our storage keys look like: "<candidate_id>/<document_type>/<filename>"
-- We extract the first part of the path and match it against the candidates table.

-- Select (Read) Policy
create policy "Candidate Read Own Objects" 
on storage.objects for select 
using (
  (select split_part(name, '/', 1))::uuid in (
    select id from candidates where profile_id = auth.uid()
  )
);

-- Insert (Write) Policy
create policy "Candidate Insert Own Objects" 
on storage.objects for insert 
with check (
  (select split_part(name, '/', 1))::uuid in (
    select id from candidates where profile_id = auth.uid()
  )
);

-- Update Policy
create policy "Candidate Update Own Objects" 
on storage.objects for update 
using (
  (select split_part(name, '/', 1))::uuid in (
    select id from candidates where profile_id = auth.uid()
  )
) with check (
  (select split_part(name, '/', 1))::uuid in (
    select id from candidates where profile_id = auth.uid()
  )
);

-- Delete Policy
create policy "Candidate Delete Own Objects" 
on storage.objects for delete 
using (
  (select split_part(name, '/', 1))::uuid in (
    select id from candidates where profile_id = auth.uid()
  )
);

GRANT USAGE ON SCHEMA storage TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA storage TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA storage TO authenticated;