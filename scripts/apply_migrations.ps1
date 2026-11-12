# Apply all SQL migrations to Supabase database
$dbUrl = (gcloud secrets versions access latest --secret=praxis-database-url --project=tradebit-396406 2>$null).Trim()
$dbUrl = $dbUrl -replace 'postgresql\+asyncpg://', 'postgresql://'
Write-Host "DB URL fetched, connecting..."

$migDir = Join-Path $PSScriptRoot "..\supabase\migrations"
$files = Get-ChildItem $migDir -Filter "*.sql" | Sort-Object Name

Write-Host "Found $($files.Count) migration files"

# Install psql via pip if needed
pip install psycopg2-binary 2>$null | Out-Null

python -c @"
import psycopg2, glob, os, sys
db_url = r'$dbUrl'
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r[0] for r in cur.fetchall()]
print(f'Existing tables: {tables or "(none)"}')
mig_dir = r'$($migDir -replace "\\", "\\")'
files = sorted(glob.glob(os.path.join(mig_dir, '*.sql')))
print(f'Applying {len(files)} migrations...')
ok = skip = fail = 0
for f in files:
    name = os.path.basename(f)
    print(f'  {name}...', end=' ', flush=True)
    with open(f, encoding='utf-8') as fh:
        sql = fh.read()
    try:
        cur.execute(sql)
        print('OK')
        ok += 1
    except Exception as e:
        err = str(e).strip()
        conn.rollback()
        if 'already exists' in err:
            print('SKIP')
            skip += 1
        else:
            print(f'ERR: {err[:120]}')
            fail += 1
try:
    cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
    for f in files:
        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING", (os.path.basename(f),))
except: pass
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f'\nFinal tables: {tables}')
print(f'Done! OK={ok} SKIP={skip} FAIL={fail}')
cur.close()
conn.close()
"@
