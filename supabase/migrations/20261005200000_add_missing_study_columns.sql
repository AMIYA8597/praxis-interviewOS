-- Add missing columns to study_items that the ORM expects
ALTER TABLE study_items ADD COLUMN IF NOT EXISTS repetitions int default 0;
ALTER TABLE study_items ADD COLUMN IF NOT EXISTS solver_result_id uuid REFERENCES solver_results(id) ON DELETE CASCADE;

-- Update source check constraint to include new source types
ALTER TABLE study_items DROP CONSTRAINT IF EXISTS study_items_source_check;
ALTER TABLE study_items ADD CONSTRAINT study_items_source_check CHECK (source in ('weak_answer','missed_concept','jd_gap','manual','screenshot_solve','generated'));

-- Add missing columns to solver_results
ALTER TABLE solver_results ADD COLUMN IF NOT EXISTS screenshot_type text;
ALTER TABLE solver_results ADD COLUMN IF NOT EXISTS hints jsonb;
