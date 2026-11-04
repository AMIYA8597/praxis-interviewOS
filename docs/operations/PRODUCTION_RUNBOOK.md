# PRAXIS InterviewOS — Day-2 Production Runbook

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Daily Health Checks & Routine Verification

Execute daily preflight checks to confirm operational health:

```bash
# 1. API Health & Liveness
curl -fsS https://<API_HOST>/api/v1/health/live
curl -fsS https://<API_HOST>/api/v1/health/ready

# 2. Provider Health & Circuit Breaker Status
curl -fsS https://<API_HOST>/api/v1/observability/provider-health \
  -H "Authorization: Bearer <ADMIN_JWT>"

# 3. System Metrics & Memory Pools
curl -fsS https://<API_HOST>/api/v1/observability/system \
  -H "Authorization: Bearer <ADMIN_JWT>"
```

---

## 2. Service Restart & Traffic Rollback Procedures

### 2.1 Restarting a Cloud Run Service
```bash
# Force immediate rolling restart by updating annotations
gcloud run services update praxis-api \
  --region=asia-south1 \
  --project=praxis-staging \
  --update-annotations="restart-timestamp=$(date +%s)"
```

### 2.2 Instant Traffic Rollback (Zero Downtime)
```bash
# Rollback traffic to previous stable revision instantly
gcloud run services update-traffic praxis-api \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=asia-south1 \
  --project=praxis-staging
```

---

## 3. Worker Queue Maintenance

```bash
# Inspect ARQ failed jobs count
psql "$DATABASE_URL" -c "SELECT job_name, count(*) FROM failed_jobs GROUP BY job_name;"

# Replay failed dead-letter jobs
python scripts/retry_failed_jobs.py
```
