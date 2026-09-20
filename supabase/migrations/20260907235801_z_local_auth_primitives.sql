-- MOCK AUTH PRIMITIVES (Local Dev Only)
-- Safe to run against real Supabase due to IF NOT EXISTS and CREATE OR REPLACE checks,
-- but typically this would be skipped in production via migration pipeline config.

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN 
        CREATE ROLE authenticated; 
    END IF; 
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role;
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS auth;

CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
DECLARE
    claims jsonb;
BEGIN
    claims := current_setting('request.jwt.claims', true)::jsonb;
    IF claims IS NULL OR claims->>'sub' IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN (claims->>'sub')::uuid;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO authenticated;

GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
