-- Role creation and credentials must be managed out-of-band (e.g. via Terraform or secure secret injection).
-- Removed hardcoded LOGIN password 'app_password'. Any database where the previous version
-- of this migration was applied MUST have its praxis_app credential rotated immediately.
DO $do$ 
BEGIN 
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'praxis_app') THEN 
    CREATE ROLE praxis_app WITH NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOLOGIN; 
  END IF; 
END $do$; 
GRANT authenticated TO praxis_app; 
GRANT USAGE ON SCHEMA public TO praxis_app; 
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO praxis_app; 
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO praxis_app; 
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO praxis_app; 
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO praxis_app;
