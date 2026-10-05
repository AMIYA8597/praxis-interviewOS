-- Phase 57 + Readiness: Preparation plans — prioritized practice schedule per candidate+job.
-- Two services write to this table with different JSON column names:
--   readiness.py (Phase 1): writes plan_sessions + is_active + completed_count
--   preparation_engine.py (Phase 57): writes plan_json
-- Both columns are nullable; generated_at is updated by whichever service last wrote.
-- UNIQUE NULLS NOT DISTINCT: treats (candidate_id, NULL) as a unique combination,
-- so a candidate can have one plan without a job and one per job.

CREATE TABLE IF NOT EXISTS preparation_plans (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  job_id          uuid REFERENCES jobs(id) ON DELETE SET NULL,
  plan_sessions   jsonb,
  plan_json       jsonb,
  is_active       boolean NOT NULL DEFAULT true,
  completed_count int NOT NULL DEFAULT 0,
  generated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (candidate_id, job_id)
);

ALTER TABLE preparation_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE preparation_plans FORCE ROW LEVEL SECURITY;

CREATE POLICY "own_preparation_plans"
  ON preparation_plans FOR ALL
  USING (candidate_id IN (
    SELECT id FROM candidates WHERE profile_id = auth.uid()
  ));

CREATE INDEX IF NOT EXISTS idx_preparation_plans_candidate
  ON preparation_plans(candidate_id);
