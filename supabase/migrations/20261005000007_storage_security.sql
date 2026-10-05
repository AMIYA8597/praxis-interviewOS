-- Phase 96 — Supabase Storage Security
--
-- Storage bucket RLS policies (private buckets, owner-only upload/read/delete,
-- service_role full access for workers) are Supabase-specific and require the
-- storage extension schema which is not present in plain PostgreSQL.
--
-- These policies are applied via the Supabase dashboard or Supabase CLI
-- separately from this migrate.py pipeline.  See:
--   docs/PRAXIS_PRODUCTION_CERTIFICATION.md § Storage Architecture
--   supabase/storage_policies.sql  (applied via: supabase db push)
--
-- This file is intentionally a no-op so that migrate.py (which runs against
-- plain PostgreSQL in CI) continues to pass.

SELECT 1; -- no-op: storage policies managed outside of migrate.py
