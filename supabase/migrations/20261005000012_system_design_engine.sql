-- Phase 62: System Design Interview Engine — per-session phase state machine.
-- One row per session; tracks current phase, completed phases, and challenge count.

CREATE TABLE IF NOT EXISTS system_design_session_state (
  session_id        uuid PRIMARY KEY REFERENCES practice_sessions(id) ON DELETE CASCADE,
  current_phase     text NOT NULL DEFAULT 'requirements_gathering',
  phases_completed  text[] NOT NULL DEFAULT '{}',
  challenge_count   int NOT NULL DEFAULT 0,
  last_updated_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE system_design_session_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_session_state FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_sd_state"
  ON system_design_session_state FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions WHERE candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  ));
