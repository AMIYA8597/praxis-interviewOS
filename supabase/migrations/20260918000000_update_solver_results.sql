ALTER TABLE solver_results ADD COLUMN screenshot_type text; ALTER TABLE solver_results ADD COLUMN hints jsonb;
ALTER TABLE study_items DROP CONSTRAINT study_items_source_check; ALTER TABLE study_items ADD CONSTRAINT study_items_source_check CHECK (source in ('weak_answer','missed_concept','jd_gap','manual','screenshot_solve')); ALTER TABLE study_items ADD COLUMN solver_result_id uuid REFERENCES solver_results(id) ON DELETE CASCADE;
ALTER TABLE study_items ADD COLUMN repetitions int default 0;
