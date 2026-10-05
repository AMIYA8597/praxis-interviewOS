# PRAXIS Backend Disaster Recovery

This document describes recovery targets, backup procedures, and step-by-step runbooks
for each failure scenario. All claims are grounded in actual code (`scripts/backup.sh`,
`infra/gcp/main.tf`).

---

## 1. Recovery Targets

| Metric | Target | Basis |
|---|---|---|
| RPO (Recovery Point Objective) | 24 hours | Daily backup schedule |
| RTO (Recovery Target Objective) | < 2 hours | Restore + schema validate + smoke test |

These targets are documented in `scripts/backup.sh` header comments.

**Point-in-time recovery (PITR)**: not available on Supabase Free tier. PITR requires
Supabase Pro plan. Until Pro is activated, the effective RPO is 24 hours (last backup).

---

## 2. Backup Procedure

Script: `scripts/backup.sh`

### Prerequisites

The following environment variables must be set (retrieved from Secret Manager in production):

```bash
SUPABASE_DB_URL="postgres://..."   # Supabase connection string
GCS_BACKUP_BUCKET="praxis-backups-production"
APP_ENV="production"               # Used in backup filename
RETAIN_DAYS=30                     # Optional; default is 30
```

### What it does

1. Runs `pg_dump --format=plain --no-owner --no-acl --quote-all-identifiers` against
   `SUPABASE_DB_URL`.
2. Pipes output through `gzip -9` into a temp file.
3. Uploads to `gs://${GCS_BACKUP_BUCKET}/praxis-${APP_ENV}-${TIMESTAMP}.sql.gz`.
4. Deletes temp file.
5. Prunes any backups older than `RETAIN_DAYS` days from the bucket.

### Filename format

`praxis-production-20260901T120000Z.sql.gz`

### Running manually

```bash
export SUPABASE_DB_URL="$(gcloud secrets versions access latest \
    --secret=praxis-database-url --project=praxis-production)"
export GCS_BACKUP_BUCKET="praxis-backups-production"
export APP_ENV="production"
bash scripts/backup.sh
```

### Scheduling

The backup script is designed to run as a Cloud Run Job on a cron schedule.
This job is **not yet provisioned** in `infra/gcp/main.tf` — must be added before
the system is considered production-ready. Until then, backups must be triggered manually
or via Cloud Scheduler calling a Cloud Run Job.

---

## 3. Restore Procedure

### Step 1: Download backup from GCS

```bash
# List available backups
gsutil ls gs://praxis-backups-production/

# Download the desired backup
gsutil cp gs://praxis-backups-production/praxis-production-<TIMESTAMP>.sql.gz \
    /tmp/praxis-backup.sql.gz
```

### Step 2: Decompress

```bash
gunzip /tmp/praxis-backup.sql.gz
# Result: /tmp/praxis-backup.sql
```

### Step 3: Restore to target database

For a plain-format dump (as produced by `backup.sh`):

```bash
psql "$SUPABASE_DB_URL" < /tmp/praxis-backup.sql
```

If restoring to a fresh Supabase project, apply migrations first to ensure extensions
(`pgvector`, `pgcrypto`) are present, then restore data only:

```bash
# Apply schema migrations first
supabase db push  # or psql < each migration file in order

# Then restore data
psql "$SUPABASE_DB_URL" < /tmp/praxis-backup.sql
```

### Step 4: Verify schema integrity

```bash
psql "$SUPABASE_DB_URL" <<'EOF'
-- Check all expected tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Check row counts for key tables
SELECT 'candidates' AS t, count(*) FROM candidates
UNION ALL SELECT 'documents', count(*) FROM documents
UNION ALL SELECT 'practice_sessions', count(*) FROM practice_sessions
UNION ALL SELECT 'study_items', count(*) FROM study_items;

-- Check RLS is enabled and forced
SELECT tablename, rowsecurity, forcerowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND (NOT rowsecurity OR NOT forcerowsecurity)
ORDER BY tablename;
-- Expected: 0 rows (all tables should have RLS+FORCE enabled)
EOF
```

### Step 5: Run RLS isolation tests

```bash
cd backend
python -m pytest tests/security/test_rls_isolation.py -v
```

### Step 6: Smoke test

```bash
# Start the API locally against the restored DB
APP_ENV=development DATABASE_URL="$SUPABASE_DB_URL" uvicorn backend.app.main:app

# In another terminal
curl http://localhost:8000/health/ready
# Expected: {"status": "ready"}
```

A backup is only counted toward the RPO if this restore procedure completes successfully.

---

## 4. Recovery Scenarios

### Scenario 1: Database corruption

**Symptoms**: Queries returning unexpected errors, constraint violations, missing rows.

**Recovery**:
1. Identify the last clean backup in GCS.
2. Provision a new Supabase project (or use a point-in-time branch on Pro).
3. Follow the full restore procedure (Steps 1–6 above).
4. Update `praxis-database-url` secret in Secret Manager to point to the new database.
5. Redeploy all Cloud Run services to pick up the new secret version:
   ```bash
   gcloud run services update praxis-api --region us-central1 --project praxis-production
   gcloud run services update praxis-realtime --region us-central1 --project praxis-production
   gcloud run services update praxis-worker --region us-central1 --project praxis-production
   ```

**Data loss**: up to 24 hours (RPO).

---

### Scenario 2: Redis unavailable

**Symptoms**: 503 errors on rate-limited endpoints, JWKS cache misses, ARQ queue not draining.

**Behavior**:
- `RateLimitMiddleware`: fails **open** — requests pass through without rate limiting.
  See `backend/app/rate_limiter.py` line: `except Exception: pass`.
- JWKS cache: re-fetched from Supabase on next request (cold path, slightly higher latency).
- ARQ queue: workers pause until Redis reconnects. Jobs already queued persist in Redis.
  No jobs are lost if Redis is durable (Memorystore persistent storage enabled).
- Budget guard: daily/session budget keys unavailable — `BudgetExceededError` may not fire;
  paid calls may proceed over budget until Redis recovers.
- Session state: resume-on-reconnect requires Redis; sessions cannot be resumed until
  Redis is available.

**Recovery**: Memorystore Redis is managed by GCP. Wait for automatic recovery.
For extended outages, provision a replacement Memorystore instance and update the
`praxis-redis-url` secret.

---

### Scenario 3: AI provider outage

**Symptoms**: Interviews stalling, study generation failing, scoring timeouts.

**Behavior**: The `GatewayRouter` circuit breaker detects consecutive failures and opens
the circuit for the affected provider. The router skips to the next candidate in the
`models.yaml` alias list. Fallback is logged as `ai_fallback` and the `fell_back_from`
column is populated in `usage_events`.

- `fast_classify`: ollama → Groq → OpenAI
- `reasoning`: ollama → Groq → OpenAI
- `deep_reasoning`: OpenAI → Anthropic → Groq → ollama

If all providers in an alias fail: `AllProvidersUnavailableError` is raised.
The endpoint returns 503. The ARQ job retries with exponential backoff (5s × 2^(try-1)).

**Recovery**: Circuit breakers self-recover when the provider responds successfully
(half-open probe). No manual action required unless all providers are simultaneously down.

---

### Scenario 4: Cloud Run revision bad

**Symptoms**: Elevated 5xx error rate, health check failures on new revision.

**Recovery**:
```bash
# List recent revisions
gcloud run revisions list --service praxis-api --region us-central1 \
    --project praxis-production

# Immediately route 100% traffic to previous revision
gcloud run services update-traffic praxis-api \
    --region us-central1 \
    --project praxis-production \
    --to-revisions praxis-api-<PREVIOUS-REVISION>=100
```

Rollback takes effect within ~30 seconds. New revision is stopped but not deleted;
it can be examined for root cause.

Repeat for `praxis-realtime` and `praxis-worker` if affected.

---

### Scenario 5: Secret compromise

**Symptoms**: Unauthorized access, token abuse, or secret rotation required after breach.

**Recovery**:
1. Rotate the compromised secret in Secret Manager:
   ```bash
   # Create a new version with the new value
   echo -n "new-secret-value" | gcloud secrets versions add <secret-name> \
       --data-file=- --project praxis-production
   ```
2. Redeploy all services that use this secret (they reference `version: latest`,
   so a redeploy picks up the new version):
   ```bash
   for svc in praxis-api praxis-realtime praxis-worker; do
     gcloud run services update $svc \
       --region us-central1 --project praxis-production --quiet
   done
   ```
3. Revoke old secret version:
   ```bash
   gcloud secrets versions disable <version-id> --secret <secret-name> \
       --project praxis-production
   ```
4. If Supabase JWT signing key is compromised: rotate via Supabase dashboard.
   All existing sessions are invalidated immediately.

---

## 5. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| PITR requires Supabase Pro | RPO = 24h; no sub-day recovery | Upgrade to Pro for production |
| Backup scheduling not yet in IaC | Backup must be triggered manually | Add Cloud Scheduler + Cloud Run Job |
| Redis persistence not explicitly configured | Jobs lost if Redis crashes without persistence | Enable Memorystore persistence flag |
| Worker is not in Terraform | Worker scaling not IaC-managed | Add `google_cloud_run_v2_job` resource |
| No automated restore verification | A backup is only validated if manually restored | Automate weekly restore test in Cloud Build |
