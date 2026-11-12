"""Run SQL migrations via Supabase Management API (HTTPS, port 443).

Works even when PostgreSQL ports (5432/6543) are blocked by the network.
Usage: python scripts/run_migrations_http.py <SUPABASE_ACCESS_TOKEN>
"""
import glob
import os
import sys
import json

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

PROJECT_REF = "rqbbfegkqmsvthdgoyqk"
API_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"


def run_sql(sql: str, token: str) -> dict:
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"query": sql},
        timeout=60,
    )
    if resp.status_code != 201 and resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    return resp.json()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migrations_http.py <SUPABASE_ACCESS_TOKEN>")
        print("\nGet your token from: https://supabase.com/dashboard/account/tokens")
        sys.exit(1)

    token = sys.argv[1]

    # Check existing tables
    result = run_sql(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name",
        token,
    )
    if "error" in result:
        print(f"ERROR connecting: {result['error']}")
        sys.exit(1)
    existing = [r.get("table_name", r) for r in result] if isinstance(result, list) else []
    print(f"Existing public tables: {existing or '(none)'}")

    # Find migration files
    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "supabase", "migrations",
    )
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
        result = run_sql(sql, token)
        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            if "already exists" in err:
                print("SKIPPED (already exists)")
                skipped += 1
            else:
                print(f"ERROR: {err[:200]}")
                failed += 1
        else:
            print("OK")
            success += 1

    # Create tracking table
    print("\n  Creating schema_migrations...", end=" ", flush=True)
    run_sql(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        token,
    )
    for f in files:
        name = os.path.basename(f)
        run_sql(
            f"INSERT INTO schema_migrations (version) VALUES ('{name}') ON CONFLICT DO NOTHING",
            token,
        )
    print("OK")

    # Verify
    result = run_sql(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name",
        token,
    )
    final = [r.get("table_name", r) for r in result] if isinstance(result, list) else result
    print(f"\nFinal public tables: {final}")
    print(f"\nDone! Success: {success}, Skipped: {skipped}, Failed: {failed}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
