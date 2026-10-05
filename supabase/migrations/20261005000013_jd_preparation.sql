-- Phase 59: JD-Driven Preparation — requirement graph and candidate evidence map.
-- jd_requirement_graph: normalized JD requirements extracted from each job posting.
-- candidate_jd_evidence: per-candidate coverage tracking against each requirement.

CREATE TABLE IF NOT EXISTS jd_requirement_graph (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id           uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  requirement_text text NOT NULL,
  domain_code      text REFERENCES interview_domains(code),
  importance       text NOT NULL DEFAULT 'required'
    CHECK (importance IN ('required', 'preferred', 'nice_to_have')),
  created_at       timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE jd_requirement_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE jd_requirement_graph FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_jd_requirements"
  ON jd_requirement_graph FOR ALL
  USING (job_id IN (
    SELECT id FROM jobs WHERE candidate_id IN (
      SELECT id FROM candidates WHERE profile_id = auth.uid()
    )
  ));

CREATE INDEX IF NOT EXISTS idx_jd_requirements_job ON jd_requirement_graph(job_id);

-- ── Candidate evidence coverage ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candidate_jd_evidence (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  requirement_id   uuid NOT NULL REFERENCES jd_requirement_graph(id) ON DELETE CASCADE,
  evidence_type    text NOT NULL DEFAULT 'session_score',
  score            numeric(5,4),
  covered          boolean NOT NULL DEFAULT false,
  last_updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, requirement_id)
);

ALTER TABLE candidate_jd_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_jd_evidence FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_jd_evidence"
  ON candidate_jd_evidence FOR ALL
  USING (candidate_id IN (
    SELECT id FROM candidates WHERE profile_id = auth.uid()
  ));

CREATE INDEX IF NOT EXISTS idx_jd_evidence_candidate
  ON candidate_jd_evidence(candidate_id);
CREATE INDEX IF NOT EXISTS idx_jd_evidence_requirement
  ON candidate_jd_evidence(requirement_id);
