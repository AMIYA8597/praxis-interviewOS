-- ============================================================
-- PHASE 11-14: Interview taxonomy, question bank, readiness
-- ============================================================

-- Canonical interview domain taxonomy
CREATE TABLE IF NOT EXISTS interview_domains (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code        text NOT NULL UNIQUE,        -- e.g. "DSA", "SYSTEM_DESIGN"
  parent_code text REFERENCES interview_domains(code),
  category    text NOT NULL,               -- "TECHNICAL" | "BEHAVIORAL" | "SPECIALIZED"
  label       text NOT NULL,
  description text,
  sort_order  int  NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Seed the canonical taxonomy
INSERT INTO interview_domains (code, parent_code, category, label, sort_order) VALUES
  -- Technical top-level
  ('TECHNICAL',         NULL,        'TECHNICAL',   'Technical',              10),
  ('DSA',               'TECHNICAL', 'TECHNICAL',   'Data Structures & Algorithms', 11),
  ('ALGORITHMS',        'TECHNICAL', 'TECHNICAL',   'Algorithms',             12),
  ('OOP',               'TECHNICAL', 'TECHNICAL',   'Object-Oriented Design', 13),
  ('OS',                'TECHNICAL', 'TECHNICAL',   'Operating Systems',      14),
  ('NETWORKING',        'TECHNICAL', 'TECHNICAL',   'Networking',             15),
  ('DATABASES',         'TECHNICAL', 'TECHNICAL',   'Databases',              16),
  ('SQL',               'TECHNICAL', 'TECHNICAL',   'SQL',                    17),
  ('DISTRIBUTED',       'TECHNICAL', 'TECHNICAL',   'Distributed Systems',    18),
  ('CONCURRENCY',       'TECHNICAL', 'TECHNICAL',   'Concurrency',            19),
  ('BACKEND',           'TECHNICAL', 'TECHNICAL',   'Backend Engineering',    20),
  ('APIS',              'TECHNICAL', 'TECHNICAL',   'API Design',             21),
  ('CACHING',           'TECHNICAL', 'TECHNICAL',   'Caching',                22),
  ('SECURITY',          'TECHNICAL', 'TECHNICAL',   'Security',               23),
  ('CLOUD',             'TECHNICAL', 'TECHNICAL',   'Cloud / Infra',          24),
  ('DEVOPS',            'TECHNICAL', 'TECHNICAL',   'DevOps / CI-CD',         25),
  ('SYSTEM_DESIGN',     'TECHNICAL', 'TECHNICAL',   'System Design',          26),
  ('LOW_LEVEL_DESIGN',  'TECHNICAL', 'TECHNICAL',   'Low-Level Design',       27),
  ('PERFORMANCE',       'TECHNICAL', 'TECHNICAL',   'Performance',            28),
  ('PROGRAMMING',       'TECHNICAL', 'TECHNICAL',   'Programming',            29),
  -- Behavioral
  ('BEHAVIORAL',        NULL,        'BEHAVIORAL',  'Behavioral',             40),
  ('LEADERSHIP',        'BEHAVIORAL','BEHAVIORAL',  'Leadership',             41),
  ('CONFLICT',          'BEHAVIORAL','BEHAVIORAL',  'Conflict Resolution',    42),
  ('FAILURE',           'BEHAVIORAL','BEHAVIORAL',  'Handling Failure',       43),
  ('OWNERSHIP',         'BEHAVIORAL','BEHAVIORAL',  'Ownership',              44),
  ('COLLABORATION',     'BEHAVIORAL','BEHAVIORAL',  'Collaboration',          45),
  ('AMBIGUITY',         'BEHAVIORAL','BEHAVIORAL',  'Handling Ambiguity',     46),
  ('PRIORITIZATION',    'BEHAVIORAL','BEHAVIORAL',  'Prioritization',         47),
  ('STAR',              'BEHAVIORAL','BEHAVIORAL',  'STAR Method',            48),
  -- Specialized
  ('SPECIALIZED',       NULL,        'SPECIALIZED', 'Specialized',            60),
  ('AI_ML',             'SPECIALIZED','SPECIALIZED','AI / ML',                61),
  ('GENAI',             'SPECIALIZED','SPECIALIZED','Generative AI',          62),
  ('LLM',               'SPECIALIZED','SPECIALIZED','LLMs',                   63),
  ('MLOPS',             'SPECIALIZED','SPECIALIZED','MLOps',                  64),
  ('BLOCKCHAIN',        'SPECIALIZED','SPECIALIZED','Blockchain',             65)
ON CONFLICT (code) DO NOTHING;

-- Question bank
CREATE TABLE IF NOT EXISTS question_bank (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_code     text NOT NULL REFERENCES interview_domains(code),
  subcategory     text,
  difficulty      text NOT NULL CHECK (difficulty IN ('easy','medium','hard','expert')),
  title           text NOT NULL,
  body            text NOT NULL,
  expected_concepts text[],
  rubric          text,
  follow_up_ids   uuid[],
  role_tags       text[],
  source          text NOT NULL DEFAULT 'human',   -- 'human' | 'ai_generated'
  quality_status  text NOT NULL DEFAULT 'approved' CHECK (quality_status IN ('draft','approved','deprecated')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_question_bank_domain ON question_bank(domain_code);
CREATE INDEX IF NOT EXISTS idx_question_bank_difficulty ON question_bank(difficulty);

-- Readiness / preparation model
CREATE TABLE IF NOT EXISTS candidate_readiness (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id        uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id              uuid REFERENCES jobs(id) ON DELETE SET NULL,
  computed_at         timestamptz NOT NULL DEFAULT now(),
  overall_score       numeric(5,2),           -- 0-100
  confidence          text,                   -- 'low' | 'medium' | 'high'
  technical_score     numeric(5,2),
  system_design_score numeric(5,2),
  behavioral_score    numeric(5,2),
  communication_score numeric(5,2),
  grounding_score     numeric(5,2),
  jd_coverage_score   numeric(5,2),
  weakest_domain      text REFERENCES interview_domains(code),
  recommended_action  text,
  component_detail    jsonb,
  UNIQUE (candidate_id, job_id)
);

-- Preparation plan sessions
CREATE TABLE IF NOT EXISTS preparation_plans (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id          uuid REFERENCES jobs(id) ON DELETE SET NULL,
  generated_at    timestamptz NOT NULL DEFAULT now(),
  plan_sessions   jsonb NOT NULL DEFAULT '[]',   -- ordered list of focus sessions
  is_active       boolean NOT NULL DEFAULT true,
  completed_count int NOT NULL DEFAULT 0,
  UNIQUE (candidate_id, job_id)
);

-- Enable RLS
ALTER TABLE interview_domains   ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank       ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_readiness ENABLE ROW LEVEL SECURITY;
ALTER TABLE preparation_plans   ENABLE ROW LEVEL SECURITY;

-- interview_domains and question_bank are read-only for all authenticated users
CREATE POLICY "authenticated_read_domains"
  ON interview_domains FOR SELECT
  USING (true);

CREATE POLICY "authenticated_read_questions"
  ON question_bank FOR SELECT
  USING (true);

-- Readiness and plans are per-candidate
CREATE POLICY "own_readiness"
  ON candidate_readiness FOR ALL
  USING (
    candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  );

CREATE POLICY "own_plans"
  ON preparation_plans FOR ALL
  USING (
    candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  );
