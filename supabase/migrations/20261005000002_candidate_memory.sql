-- ============================================================
-- PHASE 55-56: Candidate memory, personalization, interview profile
-- ============================================================

-- Structured facts observed from real sessions (not inferences)
CREATE TABLE IF NOT EXISTS candidate_topic_facts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  domain_code     text NOT NULL REFERENCES interview_domains(code),
  -- Measurable facts from real sessions
  sessions_practiced   int NOT NULL DEFAULT 0,
  questions_answered   int NOT NULL DEFAULT 0,
  correct_count        int NOT NULL DEFAULT 0,
  weak_count           int NOT NULL DEFAULT 0,   -- correctness < 0.5
  avg_correctness      numeric(5,4),
  avg_grounding        numeric(5,4),
  avg_structure        numeric(5,4),
  last_practiced_at    timestamptz,
  -- Mastery classification derived from facts (NOT stored as inference of future performance)
  mastery_status  text NOT NULL DEFAULT 'unknown'
    CHECK (mastery_status IN ('unknown','learning','developing','proficient','mastered_for_now','needs_review')),
  mastery_updated_at   timestamptz,
  -- Spaced repetition integration
  sm2_interval_days    int NOT NULL DEFAULT 1,
  sm2_ease_factor      numeric(5,4) NOT NULL DEFAULT 2.5,
  sm2_repetitions      int NOT NULL DEFAULT 0,
  next_review_at       timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, domain_code)
);

-- Structured inferences tagged as inferences (separate from facts)
CREATE TABLE IF NOT EXISTS candidate_inferences (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  domain_code     text REFERENCES interview_domains(code),
  inference_type  text NOT NULL CHECK (inference_type IN (
    'needs_more_practice', 'knowledge_gap', 'recall_success_expression_failure',
    'improvement_trend', 'regression_trend', 'mastery_decay_risk', 'recurring_mistake'
  )),
  -- The inference itself — stored with evidence
  inference_text  text NOT NULL,
  evidence_json   jsonb NOT NULL DEFAULT '{}',   -- supporting facts
  confidence      text NOT NULL DEFAULT 'low' CHECK (confidence IN ('low','medium','high')),
  generated_at    timestamptz NOT NULL DEFAULT now(),
  invalidated_at  timestamptz,   -- set when later evidence contradicts
  CONSTRAINT inference_text_not_empty CHECK (length(trim(inference_text)) > 0)
);

-- Communication profile: per-candidate aggregate from real session coaching metrics
CREATE TABLE IF NOT EXISTS candidate_communication_profile (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id        uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE UNIQUE,
  -- Derived from coaching.metrics events across all sessions
  avg_wpm             numeric(6,2),
  avg_filler_rate     numeric(5,4),
  avg_pause_count     numeric(6,2),
  avg_longest_pause_ms numeric(8,2),
  avg_answer_length_s  numeric(6,2),
  avg_structure_score  numeric(5,4),
  sessions_counted     int NOT NULL DEFAULT 0,
  top_fillers          text[],              -- most frequent fillers observed
  updated_at           timestamptz NOT NULL DEFAULT now()
);

-- Personal interview profile: derived canonical view
CREATE TABLE IF NOT EXISTS candidate_interview_profile (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id        uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE UNIQUE,
  -- Scores derived from real sessions (null = not enough data)
  dsa_score           numeric(5,2),
  backend_score       numeric(5,2),
  databases_score     numeric(5,2),
  distributed_score   numeric(5,2),
  system_design_score numeric(5,2),
  behavioral_score    numeric(5,2),
  communication_score numeric(5,2),
  grounding_score     numeric(5,2),
  -- Verified vs uncertain claim counts
  verified_claims_count   int NOT NULL DEFAULT 0,
  uncertain_claims_count  int NOT NULL DEFAULT 0,
  -- Profile metadata
  total_sessions      int NOT NULL DEFAULT 0,
  profile_version     int NOT NULL DEFAULT 1,   -- bump when recomputed
  computed_at         timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS + FORCE on all new tables
ALTER TABLE candidate_topic_facts            ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_topic_facts            FORCE ROW LEVEL SECURITY;
ALTER TABLE candidate_inferences             ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_inferences             FORCE ROW LEVEL SECURITY;
ALTER TABLE candidate_communication_profile  ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_communication_profile  FORCE ROW LEVEL SECURITY;
ALTER TABLE candidate_interview_profile      ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_interview_profile      FORCE ROW LEVEL SECURITY;

-- RLS policies — all scoped to owning candidate
CREATE POLICY "own_topic_facts"
  ON candidate_topic_facts FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE POLICY "own_inferences"
  ON candidate_inferences FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE POLICY "own_comm_profile"
  ON candidate_communication_profile FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

CREATE POLICY "own_interview_profile"
  ON candidate_interview_profile FOR ALL
  USING (candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid()));

-- Indexes
CREATE INDEX IF NOT EXISTS idx_topic_facts_candidate ON candidate_topic_facts(candidate_id);
CREATE INDEX IF NOT EXISTS idx_topic_facts_next_review ON candidate_topic_facts(next_review_at);
CREATE INDEX IF NOT EXISTS idx_inferences_candidate ON candidate_inferences(candidate_id);
