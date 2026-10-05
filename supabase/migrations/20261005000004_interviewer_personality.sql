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

-- Phase 62: System design interview flow state
CREATE TABLE IF NOT EXISTS system_design_session_state (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE UNIQUE,
  current_phase   text NOT NULL DEFAULT 'requirements_gathering'
    CHECK (current_phase IN (
      'requirements_gathering','clarification','high_level_design',
      'deep_dive_component','scalability_challenge','data_modeling',
      'api_design','failure_scenarios','optimization','wrap_up'
    )),
  phases_completed  text[] NOT NULL DEFAULT '{}',
  challenge_count   int NOT NULL DEFAULT 0,
  last_updated_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE system_design_session_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_session_state FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_sd_state"
  ON system_design_session_state FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions
    WHERE candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
  ));

-- Phase 64: Coding session state + test execution tracking
CREATE TABLE IF NOT EXISTS coding_session_state (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE UNIQUE,
  problem_id      uuid,   -- references question_bank if linked
  language        text NOT NULL DEFAULT 'python',
  current_code    text,
  test_runs       int NOT NULL DEFAULT 0,
  tests_passed    int NOT NULL DEFAULT 0,
  tests_total     int NOT NULL DEFAULT 0,
  time_limit_ms   int NOT NULL DEFAULT 2000,
  memory_limit_kb int NOT NULL DEFAULT 65536,
  started_at      timestamptz NOT NULL DEFAULT now(),
  last_run_at     timestamptz
);

ALTER TABLE coding_session_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_session_state FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_coding_state"
  ON coding_session_state FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions
    WHERE candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
  ));

CREATE TABLE IF NOT EXISTS coding_test_run_results (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
  run_number      int NOT NULL,
  code_snapshot   text NOT NULL,
  stdout          text,
  stderr          text,
  tests_passed    int NOT NULL DEFAULT 0,
  tests_failed    int NOT NULL DEFAULT 0,
  runtime_ms      int,
  memory_kb       int,
  verdict         text NOT NULL DEFAULT 'pending'
    CHECK (verdict IN ('pending','passed','failed','tle','mle','error','compile_error')),
  ran_at          timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE coding_test_run_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_test_run_results FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_coding_runs"
  ON coding_test_run_results FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions
    WHERE candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
  ));

CREATE INDEX IF NOT EXISTS idx_coding_runs_session ON coding_test_run_results(session_id);
