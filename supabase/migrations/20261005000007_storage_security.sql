-- Phase 96 — Supabase Storage Security
-- Ensure all storage buckets are private.
-- Resume files, documents, and audio must never be publicly accessible.
-- Access requires a signed URL with explicit expiry.

-- ── Enforce private buckets ────────────────────────────────────────────────────
UPDATE storage.buckets
SET public = false
WHERE name IN ('resumes', 'documents', 'audio', 'avatars');

-- ── Remove any existing public read policies on storage objects ────────────────
DROP POLICY IF EXISTS "Public read objects" ON storage.objects;
DROP POLICY IF EXISTS "Allow public downloads" ON storage.objects;
DROP POLICY IF EXISTS "public read" ON storage.objects;

-- ── Candidate upload: owner can upload to their own path ──────────────────────
CREATE POLICY IF NOT EXISTS "candidate_upload_own_files"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id IN ('resumes', 'documents')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- ── Candidate read: owner can read their own objects ──────────────────────────
CREATE POLICY IF NOT EXISTS "candidate_read_own_files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id IN ('resumes', 'documents', 'audio')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- ── Candidate delete: owner can delete their own objects ─────────────────────
CREATE POLICY IF NOT EXISTS "candidate_delete_own_files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id IN ('resumes', 'documents', 'audio')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- ── Service role can access all objects (for background workers) ──────────────
-- This is acceptable because the service role key MUST NEVER be in the browser.
-- Workers use it only server-side.
CREATE POLICY IF NOT EXISTS "service_role_full_access"
ON storage.objects
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ── Object lifecycle: audio recordings retention ──────────────────────────────
-- Audio files older than 30 days are eligible for deletion by the cleanup worker.
-- This is enforced by the ARQ cleanup job, not by this migration directly.
COMMENT ON TABLE storage.objects IS
  'audio/ prefix: cleanup worker deletes objects older than 30 days. '
  'resumes/ prefix: retained until candidate deletion request. '
  'documents/ prefix: retained until candidate deletion request.';
