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

-- Phase 59: JD requirement graph — parsed requirements with candidate evidence map
CREATE TABLE IF NOT EXISTS jd_requirement_graph (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id            uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  requirement_text  text NOT NULL,
  domain_code       text REFERENCES interview_domains(code),
  importance        text NOT NULL DEFAULT 'required' CHECK (importance IN ('required','preferred','nice_to_have')),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_jd_evidence (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id      uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  requirement_id    uuid NOT NULL REFERENCES jd_requirement_graph(id) ON DELETE CASCADE,
  evidence_type     text NOT NULL CHECK (evidence_type IN ('session_score','resume_claim','session_turn')),
  evidence_ref_id   uuid,   -- session_id or turn_id
  score             numeric(5,4),
  covered           boolean NOT NULL DEFAULT false,
  last_updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, requirement_id)
);

ALTER TABLE jd_requirement_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE jd_requirement_graph FORCE ROW LEVEL SECURITY;
ALTER TABLE candidate_jd_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_jd_evidence FORCE ROW LEVEL SECURITY;

CREATE POLICY "read_jd_requirements"
  ON jd_requirement_graph FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE POLICY "own_jd_evidence"
  ON candidate_jd_evidence FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE INDEX IF NOT EXISTS idx_jd_req_job ON jd_requirement_graph(job_id);
CREATE INDEX IF NOT EXISTS idx_jd_evidence_candidate ON candidate_jd_evidence(candidate_id);
