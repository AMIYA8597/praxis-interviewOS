# Disaster Recovery

Recovery procedures for PRAXIS backend service failures.
See also: `docs/PRODUCTION_RUNBOOK.md` for day-to-day ops.

Last reviewed: 2026-10-05

---

## RTO / RPO targets

| Tier | Service | RTO target | RPO target |
|------|---------|-----------|-----------|
| 1 — Core API | praxis-api (Cloud Run) | 10 min | 0 (stateless) |
| 1 — Realtime | praxis-realtime (Cloud Run) | 10 min | 0 (stateless) |
| 2 — Worker | praxis-worker (Cloud Run) | 30 min | 5 min (Redis queue persists) |
| 2 — Database | Supabase PostgreSQL | 1 hour | 1 hour (PITR backup) |
| 3 — Redis | Memorystore Redis | 2 hours | 1 hour (AOF persistence) |

---

## Failure scenarios

### 1. Cloud Run revision fails health check

**Detection:** Cloud Monitoring alert on `praxis_api_health` < 1.

**Recovery:**
```bash
# Roll back to the previous revision
gcloud run revisions list --service praxis-api --region us-central1 | head -5
gcloud run services update-traffic praxis-api \
  --to-revisions PREVIOUS_REVISION=100 \
  --region us-central1
```

**Root cause investigation:** `gcloud logging read 'resource.type=cloud_run_revision severity>=ERROR'`

---

### 2. Database connection exhaustion

**Detection:** `pq: sorry, too many clients already` errors in Cloud Run logs.

**Recovery:**
1. Scale down Cloud Run min instances temporarily.
2. Restart the connection pool: redeploy the revision (connections are per-instance).
3. Check `docs/DATABASE_CONNECTION_BUDGET.md` for per-service limits.
4. If persistent: enable PgBouncer transaction-mode pooling (Supabase dashboard).

---

### 3. Redis unavailable (Memorystore outage)

**Detection:** `redis.exceptions.ConnectionError` in worker logs; rate limiter degraded.

**Recovery:**
- Worker ARQ will fail to dequeue jobs. Jobs persist in Redis AOF — they resume when Redis recovers.
- Rate limiter falls back to per-process in-memory limit (less accurate but safe).
- No data loss: Redis is not the system of record for any durable data.
- GCP Memorystore auto-failover to replica is enabled (see Terraform config).

---

### 4. GCS unavailable

**Detection:** `storage.exceptions.NotFound` or 5xx from GCS in application logs.

**Impact:** Resume uploads fail; export downloads fail. Session coaching continues (no GCS dependency).

**Recovery:** GCS multi-region redundancy is GCP-managed. For prolonged outage:
1. Disable upload endpoints via feature flag (Cloud Run env var `DISABLE_UPLOADS=true`).
2. Wait for GCS recovery (typically < 1 hour per GCP SLA).

---

### 5. Database data loss (accidental deletion)

**Recovery:**
1. Stop all Cloud Run revisions to prevent further writes:
   ```bash
   gcloud run services update praxis-api --max-instances 0 --region us-central1
   ```
2. Initiate Supabase PITR restore to the point before the incident:
   - Supabase Dashboard → Settings → Database → Point-in-Time Recovery
   - BLOCKED until Supabase project is provisioned
3. After restore, redeploy with `--max-instances` restored.
4. Replay any jobs from the ARQ dead-letter queue (`failed_jobs` table) that arrived after the restore point.

**RPO:** Up to 1 hour of data loss (Supabase continuous WAL archiving).

---

### 6. AI provider outage

**Detection:** `check_provider_health` cron job alert; elevated 503 rate on coaching endpoints.

**Impact:** Session debriefs, hints, JD analysis fail. Core session flow (without AI coaching) continues.

**Recovery:**
- All LLM-dependent code has explicit fallback paths that return `ServiceUnavailableError`
  (never fabricated data).
- ARQ worker retries transient failures with exponential backoff (max 3 attempts).
- If prolonged: switch the active provider alias in `config/models.yaml` + redeploy.

---

### 7. Complete service loss (region outage)

**Recovery (manual failover, BLOCKED — no multi-region setup yet):**
1. Apply Terraform to a secondary GCP region.
2. Update DNS to the new ALB IP.
3. Restore database from latest Supabase backup.
4. Estimated time: 2-4 hours.

**Current state:** Single-region deployment. Multi-region is a future milestone.

---

## Backup verification

| Schedule | Action |
|----------|--------|
| Monthly | Restore Supabase backup to a test project and run migration smoke tests |
| Quarterly | Full DR drill (simulate region outage, execute failover runbook) |

---

## Incident communication

1. Engineering on-call detects via Cloud Monitoring alert.
2. Incident declared in Slack #incidents channel.
3. Status page updated within 15 minutes of incident declaration.
4. Post-mortem within 72 hours of resolution.
