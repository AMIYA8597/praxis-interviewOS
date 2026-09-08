-- Migration: Add processing_status and error_message to jobs table

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS processing_status text NOT NULL DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE jobs
ADD CONSTRAINT valid_job_processing_status CHECK (processing_status IN ('pending', 'parsing', 'ready', 'failed'));
