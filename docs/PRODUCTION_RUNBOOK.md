# PRAXIS Production Runbook
**Phase 118**

---

## Deployment

```bash
# 1. Ensure staging E2E passed
# 2. Tag the release
git tag -a v2026.10.1 -m "Release 2026.10.1"
git push origin v2026.10.1

# 3. Trigger production deploy (via GitHub Actions or manually)
gcloud run deploy praxis-api \
  --image us-central1-docker.pkg.dev/praxis-production/praxis/praxis-api:v2026.10.1 \
  --region us-central1 --project praxis-production \
  --tag prod

# 4. Send 10% traffic to new revision
gcloud run services update-traffic praxis-api \
  --to-tags=prod=10,LATEST=90 --region us-central1

# 5. Monitor for 10 minutes, then promote
gcloud run services update-traffic praxis-api --to-latest --region us-central1
```

## Rollback

```bash
# Immediate: revert to previous revision
gcloud run services update-traffic praxis-api \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region us-central1 --project praxis-production

# Verify
curl -fsS https://api.praxis.example.com/health
```

## Migration

```bash
# ALWAYS: verify backup exists first (Supabase dashboard → Backups)
# Run on staging first
python scripts/migrate.py  # staging DB

# Verify idempotency
python scripts/migrate.py  # must print "No new migrations"

# Production
DATABASE_URL=<prod-url> python scripts/migrate.py

# Monitor for errors in Cloud Logging for 15 minutes
```

## Redis Failure

```
Symptom: worker_queue_backlog alert fires; API returns 503 on queue-dependent endpoints
Actions:
1. Check Memorystore: GCP Console → Memorystore → praxis-production → status
2. If Redis is up: check VPC connectivity (VPC Access connector)
3. If Redis is down: Memorystore auto-recovers (Basic tier SLA: 99.9%)
4. App degrades gracefully: session state falls back to DB; workers reconnect automatically
5. Once Redis recovers: workers drain backlog automatically
```

## Supabase Failure

```
Symptom: database_connectivity_failure alert; 503 on API
Actions:
1. Check https://status.supabase.com
2. Check Supabase dashboard for your project
3. Switch app to maintenance mode via Vercel environment variable:
   NEXT_PUBLIC_MAINTENANCE_MODE=true
4. Wait for Supabase recovery
5. Remove maintenance mode
```

## AI Provider Failure

```
Symptom: ai_provider_error_rate alert fires
Actions:
1. The AI Gateway automatically falls back to the next provider in the chain
2. Check which provider is failing: GET /api/v1/observability/provider-health
3. If all providers fail: set PRAXIS_ZERO_SPEND=true to halt AI calls gracefully
4. Users see degraded-mode messaging (not a crash)
5. Re-enable when provider recovers: unset PRAXIS_ZERO_SPEND
```

## Realtime Failure

```
Symptom: realtime_5xx alert; WebSocket connections failing
Actions:
1. Check Cloud Run realtime service: gcloud run services describe praxis-realtime
2. Check container logs: gcloud logging read "resource.labels.service_name=praxis-realtime" --limit 50
3. If OOM: increase memory limit via Terraform
4. If crash loop: roll back revision
5. Active sessions: clients reconnect automatically (RealtimeClient with backoff)
```

## Secret Rotation

```bash
# Rotate Supabase JWT secret
# 1. Generate new secret in Supabase dashboard
# 2. Add new version in Secret Manager (do NOT delete old version yet)
gcloud secrets versions add praxis-supabase-jwt-secret \
  --data-file=new-secret.txt

# 3. Deploy with new secret (rolling deploy)
# 4. Verify auth works
# 5. After 1h (all old tokens expired), delete old secret version
gcloud secrets versions destroy OLD_VERSION_ID \
  --secret=praxis-supabase-jwt-secret
```

## Credential Compromise

```
Immediate actions:
1. Rotate compromised credential in its source system
2. Update Secret Manager
3. Re-deploy all Cloud Run services (picks up new secret version)
4. Check access logs for unauthorized use
5. File incident report

If service role key compromised:
1. Rotate in Supabase immediately
2. All service_role operations will fail until new key is deployed
3. Emergency deploy: update Secret Manager → redeploy services
```

## High Latency

```
Symptom: api_latency alert fires (p95 > 3s)
Actions:
1. Check Cloud Trace for slow spans
2. Check DB query latency: Supabase → Query Performance
3. Check AI provider latency: GET /api/v1/observability/cost-latency
4. If DB: check connection pool exhaustion (DB_POOL_SIZE too small for instance count)
5. If AI: slowest provider may have been selected; check fallback chain
6. If Cloud Run cold starts: increase min-instances via Terraform
```

## Database Saturation

```
Symptom: Supabase connections at limit; 503 errors
Actions:
1. Check: Supabase dashboard → Database → Connection pool
2. Fix: reduce DB_POOL_SIZE in Cloud Run environment variables
   (current: 10; try 3 per instance with 2 Cloud Run instances)
3. Long-term: enable Supabase Supavisor connection pooling
```

## Queue Backlog

```
Symptom: worker_backlog alert (> 1000 jobs for 10 min)
Actions:
1. Check worker logs: gcloud logging read "resource.labels.service_name=praxis-worker"
2. Scale up worker instances: update Terraform max_instances for worker
3. If jobs are failing: check worker_idempotency_log for failed status
4. Dead-lettered jobs: manually requeue via ARQ admin or database update
```

## Vercel Outage

```
Symptom: Web app unreachable; https://www.vercel-status.com shows incident
Actions:
1. This is outside our control
2. Desktop app continues to work (connects directly to API/realtime)
3. Set status page message if prolonged
4. Vercel outages are typically resolved in < 30 min
```

## GCP Outage (Regional)

```
Symptom: us-central1 services unavailable
Actions:
1. Check https://status.cloud.google.com
2. If prolonged: activate DR plan
3. DR procedure is documented in docs/ARCHITECTURE_PRODUCTION.md
4. Supabase (separate infrastructure) remains available
```
