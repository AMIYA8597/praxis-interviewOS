DO $do$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' AND tablename != 'schema_migrations'
    LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(r.tablename) || ' FORCE ROW LEVEL SECURITY';
    END LOOP;
END $do$;
