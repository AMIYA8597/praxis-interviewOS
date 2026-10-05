-- Phase 111 -- Feature Flags: add scope support
-- The feature_flags table was created in 20260907235800_init_core_schema.sql
-- with columns (id, name, is_enabled, created_at, updated_at).
-- This migration adds description and scope/scope_value so flags can be
-- targeted at specific environments, roles, or individual candidates.

ALTER TABLE feature_flags
    ADD COLUMN IF NOT EXISTS description  TEXT,
    ADD COLUMN IF NOT EXISTS scope        TEXT NOT NULL DEFAULT 'global',
    ADD COLUMN IF NOT EXISTS scope_value  TEXT;

CREATE INDEX IF NOT EXISTS idx_feature_flags_scope
    ON feature_flags (scope, scope_value);

COMMENT ON TABLE feature_flags IS
    'Backend-owned feature flags. is_enabled applies when scope conditions match. Admin-managed.';
