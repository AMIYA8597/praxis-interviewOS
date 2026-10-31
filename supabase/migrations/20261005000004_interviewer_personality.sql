-- Phase 61: Interviewer personality modes
-- Personality changes the STYLE, not the rubric. Rubric is constant.

CREATE TABLE IF NOT EXISTS session_interviewer_config (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE UNIQUE,
  personality     text NOT NULL DEFAULT 'neutral'
    CHECK (personality IN ('neutral','technical','strict','faang_style','supportive','pressure_test')),
  -- Human-readable description of what this personality does
  description     text,
  set_at          timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE session_interviewer_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_interviewer_config FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_interviewer_config"
  ON session_interviewer_config FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions
    WHERE candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
  ));
