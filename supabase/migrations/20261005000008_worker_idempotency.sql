-- Phase 107 — Worker Idempotency Log
-- Prevents duplicate execution of irreversible worker operations.

CREATE TABLE IF NOT EXISTS worker_idempotency_log (
    idempotency_key TEXT PRIMARY KEY,
    job_type        TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE worker_idempotency_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_idempotency_log FORCE ROW LEVEL SECURITY;

-- Only the service role (background workers) may read/write idempotency records.
-- Candidates have no access to this table.
CREATE POLICY "service_role_only"
ON worker_idempotency_log
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Clean up old completed records after 7 days (run by ARQ maintenance job).
CREATE INDEX IF NOT EXISTS idx_worker_idempotency_started_at
ON worker_idempotency_log (started_at)
WHERE status = 'completed';
