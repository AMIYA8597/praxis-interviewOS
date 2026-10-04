-- MOCK AUTH PRIMITIVES (Local Dev Only)
-- Safe to run against real Supabase: roles and schema use IF NOT EXISTS guards,
-- and auth.uid() is only created when it does not already exist, so Supabase's
-- native implementation (owned by supabase_auth_admin) is never replaced.

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

DO $guard$
BEGIN
    IF to_regprocedure('auth.uid()') IS NULL THEN
        EXECUTE $fn$
            CREATE FUNCTION auth.uid() RETURNS uuid AS $body$
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
            $body$ LANGUAGE plpgsql STABLE;
        $fn$;
    END IF;
END $guard$;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO authenticated;

GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
