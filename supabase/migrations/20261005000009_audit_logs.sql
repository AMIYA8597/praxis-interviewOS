-- Phase 109 — Audit Log
-- Immutable security and business event log.
-- The backend ORM model (AuditLog) references this table.
-- NEVER UPDATE rows in this table — audit records are append-only.

CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id  UUID        REFERENCES profiles (id) ON DELETE SET NULL,
    action      TEXT        NOT NULL,
    resource    TEXT,
    details     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for per-user audit queries (admin/support diagnostics).
CREATE INDEX IF NOT EXISTS idx_audit_logs_profile_id ON audit_logs (profile_id);
-- Index for recent-event queries sorted by time.
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at  ON audit_logs (created_at DESC);

-- RLS: only admins may read/write; no candidate self-read (prevents information leak via their own log).
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- Use idempotent policy creation so the migration is safe to re-apply.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='audit_logs' AND policyname='audit_logs_select_admin') THEN
    EXECUTE 'CREATE POLICY "audit_logs_select_admin" ON audit_logs FOR SELECT USING (is_admin())';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='audit_logs' AND policyname='audit_logs_insert_admin') THEN
    EXECUTE 'CREATE POLICY "audit_logs_insert_admin" ON audit_logs FOR INSERT WITH CHECK (is_admin())';
  END IF;
END $$;
-- No UPDATE or DELETE policies — audit logs are append-only.

COMMENT ON TABLE audit_logs IS
    'Immutable security/business audit trail. Append-only. Admin-access only.';
