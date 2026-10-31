-- Phase 60: Adaptive difficulty tracking per-session
-- Tracks difficulty from REAL answer signals, not a static setting.

CREATE TABLE IF NOT EXISTS session_difficulty_state (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE UNIQUE,
  current_level   numeric(4,3) NOT NULL DEFAULT 0.500,  -- [0.0, 1.0]; 0.5 = medium
  questions_asked int NOT NULL DEFAULT 0,
  correct_streak  int NOT NULL DEFAULT 0,
  incorrect_streak int NOT NULL DEFAULT 0,
  last_updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE session_difficulty_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_difficulty_state FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_difficulty_state"
  ON session_difficulty_state FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions
    WHERE candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
  ));
