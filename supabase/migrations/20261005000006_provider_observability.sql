-- Phase 75-76: Provider resilience tracking + cost/latency intelligence

CREATE TABLE IF NOT EXISTS ai_provider_call_log (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    uuid REFERENCES candidates(id) ON DELETE SET NULL,
  session_id      uuid REFERENCES practice_sessions(id) ON DELETE SET NULL,
  alias           text NOT NULL,          -- e.g. "fast_classify", "deep_reasoning"
  provider        text NOT NULL,          -- e.g. "anthropic", "openai", "groq"
  model           text NOT NULL,
  mode            text,                   -- "generate", "generate_structured", etc.
  latency_ms      int,
  input_tokens    int,
  output_tokens   int,
  cost_usd        numeric(10,6),
  ai_mode         text NOT NULL DEFAULT 'real'
    CHECK (ai_mode IN ('real','fallback','degraded')),
  success         boolean NOT NULL DEFAULT true,
  error_type      text,
  called_at       timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ai_provider_call_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider_call_log FORCE ROW LEVEL SECURITY;

-- Admins can read all; candidates can read their own
CREATE POLICY "own_ai_calls"
  ON ai_provider_call_log FOR SELECT
  USING (
    candidate_id IN (SELECT id FROM candidates WHERE profile_id = auth.uid())
    OR auth.uid() IN (SELECT profile_id FROM candidates WHERE role = 'admin')
  );

CREATE INDEX IF NOT EXISTS idx_ai_log_session ON ai_provider_call_log(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_log_provider ON ai_provider_call_log(provider, called_at);
CREATE INDEX IF NOT EXISTS idx_ai_log_alias ON ai_provider_call_log(alias, called_at);
