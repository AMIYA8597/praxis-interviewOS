-- Phase 96 — Supabase Storage Security
-- Ensures all storage buckets are private and access-controlled.
-- Resume files, documents, and audio must never be publicly accessible.
--
-- This migration is a no-op in plain PostgreSQL CI environments
-- (no Supabase storage schema present).

DO $$
BEGIN
  -- Skip entirely on plain PostgreSQL (CI). storage schema is Supabase-only.
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage'
  ) THEN
    RAISE NOTICE 'storage schema not present — skipping storage security migration';
    RETURN;
  END IF;

  -- Enforce private buckets
  UPDATE storage.buckets
  SET public = false
  WHERE name = ANY(ARRAY['resumes', 'documents', 'audio', 'avatars']);

  -- Remove any existing public read policies
  DROP POLICY IF EXISTS "Public read objects"   ON storage.objects;
  DROP POLICY IF EXISTS "Allow public downloads" ON storage.objects;
  DROP POLICY IF EXISTS "public read"            ON storage.objects;

  -- Candidate upload: owner can upload to their own path
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects'
      AND policyname = 'candidate_upload_own_files'
  ) THEN
    CREATE POLICY "candidate_upload_own_files"
    ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (
      bucket_id = ANY(ARRAY['resumes', 'documents'])
      AND (storage.foldername(name))[1] = auth.uid()::text
    );
  END IF;

  -- Candidate read: owner can read their own objects
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects'
      AND policyname = 'candidate_read_own_files'
  ) THEN
    CREATE POLICY "candidate_read_own_files"
    ON storage.objects FOR SELECT TO authenticated
    USING (
      bucket_id = ANY(ARRAY['resumes', 'documents', 'audio'])
      AND (storage.foldername(name))[1] = auth.uid()::text
    );
  END IF;

  -- Candidate delete: owner can delete their own objects
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects'
      AND policyname = 'candidate_delete_own_files'
  ) THEN
    CREATE POLICY "candidate_delete_own_files"
    ON storage.objects FOR DELETE TO authenticated
    USING (
      bucket_id = ANY(ARRAY['resumes', 'documents', 'audio'])
      AND (storage.foldername(name))[1] = auth.uid()::text
    );
  END IF;

  -- Service role full access for background workers
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects'
      AND policyname = 'service_role_full_access'
  ) THEN
    CREATE POLICY "service_role_full_access"
    ON storage.objects FOR ALL TO service_role
    USING (true) WITH CHECK (true);
  END IF;

END;
$$;
