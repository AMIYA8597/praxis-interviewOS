-- Phase 115 — Candidate Data Export
-- GDPR/CCPA-style self-service data export.
-- Each row tracks one export job initiated by a candidate.

CREATE TABLE IF NOT EXISTS candidate_data_exports (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    status          text NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processing', 'ready', 'failed', 'expired')),
    requested_at    timestamptz NOT NULL DEFAULT now(),
    completed_at    timestamptz,
    expires_at      timestamptz,          -- when the signed download URL expires
    download_url    text,                 -- GCS signed URL (populated when status='ready')
    error_message   text,
    object_key      text,                 -- GCS object path for internal bookkeeping
    CONSTRAINT chk_ready_has_url
      CHECK (status != 'ready' OR (download_url IS NOT NULL AND expires_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_data_exports_candidate
    ON candidate_data_exports (candidate_id, requested_at DESC);

ALTER TABLE candidate_data_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_data_exports FORCE ROW LEVEL SECURITY;

-- Candidates may only see their own export records.
CREATE POLICY "candidate_owns_export"
ON candidate_data_exports
FOR ALL
USING (
    candidate_id IN (
        SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
)
WITH CHECK (
    candidate_id IN (
        SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
);
