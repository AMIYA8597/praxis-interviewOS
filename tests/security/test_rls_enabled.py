


# Tables allowed to NOT have RLS (e.g. none, or explicitly documented exceptions)
RLS_EXCEPTIONS = {'schema_migrations'} # Even 'skills' has RLS enabled, just a permissive policy

def test_all_tables_have_rls_enabled(db_conn):
    """
    CI Guard: Ensures every table in the public schema has RLS enabled.
    This prevents accidental data leaks when new tables are added.
    """
    cur = db_conn.cursor()
    
    cur.execute("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' 
          AND c.relkind = 'r'
          AND c.relname NOT LIKE 'pg_%';
    """)
    
    tables = cur.fetchall()
    
    missing_rls = []
    missing_force = []
    for table_name, rls_enabled, force_enabled in tables:
        if table_name not in RLS_EXCEPTIONS:
            if not rls_enabled:
                missing_rls.append(table_name)
            if not force_enabled:
                missing_force.append(table_name)
            
    assert not missing_rls, f"FATAL: The following tables do NOT have RLS enabled: {missing_rls}. Enable RLS immediately."
    assert not missing_force, f"FATAL: The following tables do NOT have FORCE ROW LEVEL SECURITY: {missing_force}. Force RLS immediately."
