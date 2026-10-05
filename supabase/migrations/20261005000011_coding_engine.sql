-- Phase 64: Coding Interview Engine — session state + test run results
-- coding_session_state: one row per coding practice session, tracks current code + run statistics.
-- coding_test_run_results: immutable audit log of every code execution run.

CREATE TABLE IF NOT EXISTS coding_session_state (
  session_id    uuid PRIMARY KEY REFERENCES practice_sessions(id) ON DELETE CASCADE,
  language      text NOT NULL DEFAULT 'python',
  current_code  text NOT NULL DEFAULT '',
  test_runs     int NOT NULL DEFAULT 0,
  tests_passed  int NOT NULL DEFAULT 0,
  tests_total   int NOT NULL DEFAULT 0,
  last_run_at   timestamptz
);

ALTER TABLE coding_session_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_session_state FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_coding_state"
  ON coding_session_state FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions WHERE candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  ));

-- ── Test run log ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS coding_test_run_results (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
  run_number    int NOT NULL,
  code_snapshot text NOT NULL,
  stdout        text NOT NULL DEFAULT '',
  stderr        text NOT NULL DEFAULT '',
  tests_passed  int NOT NULL DEFAULT 0,
  tests_failed  int NOT NULL DEFAULT 0,
  runtime_ms    int NOT NULL DEFAULT 0,
  verdict       text NOT NULL CHECK (verdict IN ('passed', 'failed', 'error', 'tle')),
  ran_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, run_number)
);

ALTER TABLE coding_test_run_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_test_run_results FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_coding_runs"
  ON coding_test_run_results FOR ALL
  USING (session_id IN (
    SELECT id FROM practice_sessions WHERE candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  ));

CREATE INDEX IF NOT EXISTS idx_coding_run_results_session
  ON coding_test_run_results(session_id, run_number);
