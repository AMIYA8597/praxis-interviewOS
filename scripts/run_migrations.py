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
    if not url:
        print("ERROR: Could not fetch database URL from Secret Manager")
        print("stderr:", result.stderr)
        sys.exit(1)
    return url

def run_migrations(db_url):
    import psycopg2
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supabase", "migrations")
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    print(f"Found {len(files)} migration files")

    for f in files:
        name = os.path.basename(f)
        print(f"  Applying {name}...", end=" ", flush=True)
        with open(f, "r", encoding="utf-8") as fh:
            sql = fh.read()
        try:
            cur.execute(sql)
            print("OK")
        except Exception as e:
            err = str(e)
            if "already exists" in err:
                print("SKIPPED (already exists)")
            else:
                print(f"ERROR: {err}")

    cur.close()
    conn.close()
    print("\nAll migrations applied!")

if __name__ == "__main__":
    db_url = get_database_url()
    host = db_url.split("@")[-1].split("/")[0] if "@" in db_url else "unknown"
    print(f"Connecting to: ...{host}")
    run_migrations(db_url)
