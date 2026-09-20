import os
import psycopg2
import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://praxis@localhost:5432/praxis")

# Tables allowed to NOT have RLS (e.g. none, or explicitly documented exceptions)
RLS_EXCEPTIONS = {'schema_migrations'} # Even 'skills' has RLS enabled, just a permissive policy

def test_all_tables_have_rls_enabled():
    """
    CI Guard: Ensures every table in the public schema has RLS enabled.
    This prevents accidental data leaks when new tables are added.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT c.relname, c.relrowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' 
          AND c.relkind = 'r'
          AND c.relname NOT LIKE 'pg_%';
    """)
    
    tables = cur.fetchall()
    conn.close()
    
    missing_rls = []
    for table_name, rls_enabled in tables:
        if not rls_enabled and table_name not in RLS_EXCEPTIONS:
            missing_rls.append(table_name)
            
    assert not missing_rls, f"FATAL: The following tables do NOT have RLS enabled: {missing_rls}. Enable RLS immediately."
