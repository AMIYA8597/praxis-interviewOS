-- Phase 66-74: Session analytics, weakness tracking, answer replay, memory safety

-- Phase 67: Session comparison snapshots
CREATE TABLE IF NOT EXISTS session_performance_snapshots (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  session_id      uuid NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE UNIQUE,
  overall_score   numeric(5,4),
  correctness     numeric(5,4),
  structure       numeric(5,4),
  grounding       numeric(5,4),
  specificity     numeric(5,4),
  conciseness     numeric(5,4),
  avg_wpm         numeric(6,2),
  filler_rate     numeric(5,4),
  turns_count     int NOT NULL DEFAULT 0,
  snapped_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE session_performance_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_performance_snapshots FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_snapshots"
  ON session_performance_snapshots FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

-- Phase 68: Evidence-backed weakness detection
CREATE TABLE IF NOT EXISTS candidate_weaknesses (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  weakness_type   text NOT NULL CHECK (weakness_type IN (
    'knowledge_gap','communication','grounding','structure','specificity',
    'star_completeness','hallucination','conciseness','latency'
  )),
  domain_code     text REFERENCES interview_domains(code),
  description     text NOT NULL,
  evidence_json   jsonb NOT NULL DEFAULT '{}',
  occurrence_count int NOT NULL DEFAULT 1,
  severity        text NOT NULL DEFAULT 'low' CHECK (severity IN ('low','medium','high')),
  first_observed_at timestamptz NOT NULL DEFAULT now(),
  last_observed_at  timestamptz NOT NULL DEFAULT now(),
  resolved_at     timestamptz,
  UNIQUE (candidate_id, weakness_type, domain_code)
);

ALTER TABLE candidate_weaknesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_weaknesses FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_weaknesses"
  ON candidate_weaknesses FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

-- Phase 72: Answer replay — stores multiple attempts on the same question
CREATE TABLE IF NOT EXISTS answer_attempts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  question_id     uuid REFERENCES question_bank(id),
  attempt_number  int NOT NULL DEFAULT 1,
  answer_text     text NOT NULL,
  overall_score   numeric(5,4),
  rationale       text,
  answered_at     timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE answer_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE answer_attempts FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_attempts"
  ON answer_attempts FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE INDEX IF NOT EXISTS idx_answer_attempts_candidate ON answer_attempts(candidate_id);
CREATE INDEX IF NOT EXISTS idx_answer_attempts_question ON answer_attempts(question_id, candidate_id);

-- Phase 73: Ideal answer / improvement mode
CREATE TABLE IF NOT EXISTS ideal_answer_feedback (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  question_id     uuid REFERENCES question_bank(id),
  session_id      uuid REFERENCES practice_sessions(id),
  turn_id         uuid REFERENCES session_turns(id),
  what_was_correct  text,
  what_was_missing  text,
  what_was_stronger text,
  example_answer    text,
  generated_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ideal_answer_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE ideal_answer_feedback FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_ideal_feedback"
  ON ideal_answer_feedback FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE INDEX IF NOT EXISTS idx_ideal_answer_session ON ideal_answer_feedback(session_id);
