-- Supabase Storage Security Policies
-- Phase 96
--
-- Apply via Supabase CLI: supabase db push
-- Or paste into Supabase SQL Editor (dashboard → SQL Editor).
--
-- NOT run by scripts/migrate.py (requires Supabase storage extension).

-- Enforce private buckets
UPDATE storage.buckets
SET public = false
WHERE name IN ('resumes', 'documents', 'audio', 'avatars');

-- Remove any public read policies
DROP POLICY IF EXISTS "Public read objects"    ON storage.objects;
DROP POLICY IF EXISTS "Allow public downloads" ON storage.objects;
DROP POLICY IF EXISTS "public read"            ON storage.objects;

-- Candidate upload: owner can upload to their own path
CREATE POLICY IF NOT EXISTS "candidate_upload_own_files"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id IN ('resumes', 'documents')
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Candidate read: owner can read their own objects
CREATE POLICY IF NOT EXISTS "candidate_read_own_files"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id IN ('resumes', 'documents', 'audio')
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Candidate delete: owner can delete their own objects
CREATE POLICY IF NOT EXISTS "candidate_delete_own_files"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id IN ('resumes', 'documents', 'audio')
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Service role full access for background workers
CREATE POLICY IF NOT EXISTS "service_role_full_access"
ON storage.objects FOR ALL TO service_role
USING (true) WITH CHECK (true);
