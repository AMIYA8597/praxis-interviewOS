"""Run all SQL migrations against the production Supabase database.

Usage: python scripts/run_migrations.py
Fetches DATABASE_URL from GCP Secret Manager automatically.
"""
import glob
import os
import subprocess
import sys


def get_database_url():
    result = subprocess.run(
        ["gcloud", "secrets", "versions", "access", "latest",
         "--secret=praxis-database-url", "--project=tradebit-396406"],
        capture_output=True, text=True, shell=True
    )
    url = result.stdout.strip().replace('\r', '').replace('\n', '')
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    # Try direct DB host instead of pooler (pooler may be blocked by firewall)
    url = url.replace('aws-1-eu-central-1.pooler.supabase.com:5432', 'db.rqbbfegkqmsvthdgoyqk.supabase.co:5432')
    if not url:
        print("ERROR: Could not fetch database URL from Secret Manager")
        print("stderr:", result.stderr)
        sys.exit(1)
    return url


def run_migrations(db_url):
    try:
        import psycopg2
    except ImportError:
        print("Installing psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2

    conn = psycopg2.connect(db_url, connect_timeout=15, sslmode='require')
    conn.autocommit = False
    cur = conn.cursor()

    # Check what tables already exist
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    existing_tables = [r[0] for r in cur.fetchall()]
    print(f"Existing public tables: {existing_tables or '(none)'}")
    conn.commit()

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supabase", "migrations")
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    print(f"Found {len(files)} migration files\n")

    success = 0
    skipped = 0
    failed = 0

    for f in files:
        name = os.path.basename(f)
        print(f"  Applying {name}...", end=" ", flush=True)
        with open(f, "r", encoding="utf-8") as fh:
            sql = fh.read()
        try:
            cur.execute(sql)
            conn.commit()
            print("OK")
            success += 1
        except Exception as e:
            conn.rollback()
            err = str(e).strip()
            if "already exists" in err:
                print("SKIPPED (already exists)")
                skipped += 1
            else:
                print(f"ERROR: {err}")
                failed += 1

    # Create schema_migrations tracking table
    print("\n  Creating schema_migrations table...", end=" ", flush=True)
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        conn.commit()
        for f in files:
            name = os.path.basename(f)
            cur.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                (name,)
            )
        conn.commit()
        print("OK")
    except Exception as e:
        conn.rollback()
        print(f"WARNING: {e}")

    # Verify tables were created
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    final_tables = [r[0] for r in cur.fetchall()]
    print(f"\nFinal public tables: {final_tables}")

    cur.close()
    conn.close()
    print(f"\nDone! Success: {success}, Skipped: {skipped}, Failed: {failed}")
    if failed > 0:
        print("WARNING: Some migrations failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    db_url = get_database_url()
    host = db_url.split("@")[-1].split("/")[0] if "@" in db_url else "unknown"
    print(f"Connecting to: ...{host}")
    run_migrations(db_url)
