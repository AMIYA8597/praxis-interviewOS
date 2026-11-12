-- Add score_json column to session_turns for readiness scoring queries
ALTER TABLE session_turns ADD COLUMN IF NOT EXISTS score_json jsonb;
