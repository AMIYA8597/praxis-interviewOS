# PRAXIS Production Runbook

**Status: PRE-PRODUCTION — steps are written and tested against the architecture; real execution requires provisioned staging.**

---

## 1. Deploy a new version

```bash
# Triggered automatically by git push to main.
# Manual trigger:
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --substitutions="_STAGING_PROJECT=praxis-staging,_REGISTRY_PROJECT=praxis-staging,_REGION=us-central1" \
  --project=praxis-staging

# After staging certification, deploy to production:
# 1. Get the staging-release.json from the successful staging build
# 2. Extract api_digest, realtime_digest, worker_digest
# 3. Apply Terraform with the digest:
cd infra/gcp/environments/production
terraform apply \
  -var-file=terraform.tfvars \
  -var="image_tag=<digest_from_staging_release>"
```

---

## 2. Rollback to previous revision

```bash
# List revisions:
gcloud run revisions list --service=praxis-api --region=us-central1 --project=praxis-production

# Roll back traffic to a specific revision:
gcloud run services update-traffic praxis-api \
  --to-revisions=praxis-api-REVISION_NAME=100 \
  --region=us-central1 \
  --project=praxis-production
```

**Important**: Rolling back the application does not roll back database migrations. Migrations must be forward-compatible. Never apply a migration that breaks the previous revision before the new revision is stable.

---

## 3. Scale Cloud Run services

```bash
# Increase max instances for praxis-api:
gcloud run services update praxis-api \
  --max-instances=20 \
  --region=us-central1 \
  --project=praxis-production
```

Or update `api_max_instances` in `infra/gcp/environments/production/terraform.tfvars` and apply.

---

## 4. Rotate a secret

```bash
# Create a new version of a secret:
echo -n "NEW_VALUE" | gcloud secrets versions add praxis-groq-api-key \
  --data-file=- --project=praxis-production

# Update Cloud Run to use the new version:
# Option A: update secret_version in terraform.tfvars and apply
# Option B: direct update (for emergency rotation):
gcloud run services update praxis-api \
  --update-secrets="GROQ_API_KEY=praxis-groq-api-key:NEW_VERSION" \
  --region=us-central1 \
  --project=praxis-production

# After confirming the new version works, disable the old version:
gcloud secrets versions disable OLD_VERSION \
  --secret=praxis-groq-api-key \
  --project=praxis-production
```

---

## 5. Run database migrations (staging)

```bash
supabase login
supabase link --project-ref STAGING_PROJECT_REF
supabase db push
# Verify schema after push:
supabase db inspect
```

---

## 6. Check service health

```bash
# API liveness:
curl https://api.DOMAIN/api/v1/health/live

# API readiness:
curl https://api.DOMAIN/api/v1/health/ready

# Realtime health:
curl https://realtime.DOMAIN/health/live

# Prometheus metrics:
curl https://api.DOMAIN/metrics
```

---

## 7. Investigate a 5xx spike

1. Check Cloud Logging:
   ```bash
   gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' \
     --project=praxis-production --limit=50
   ```

2. Check the alert: Cloud Monitoring → Alerting → Incidents

3. Check if it correlates with a recent deployment:
   ```bash
   gcloud run revisions list --service=praxis-api --region=us-central1 \
     --project=praxis-production --limit=5
   ```

4. If a bad deployment: rollback (see section 2 above).

---

## 8. Restart a worker

Workers are Cloud Run Worker Pools. To restart (re-deploy):
```bash
gcloud run worker-pools deploy praxis-worker \
  --image=CURRENT_IMAGE \
  --region=us-central1 \
  --project=praxis-production
```

Or: increment `worker_instance_count` and re-apply Terraform.

---

## 9. Clear stuck ARQ jobs

```bash
# Connect to Redis (from a Cloud Run job or via private VPC):
redis-cli -h REDIS_HOST

# Inspect stuck jobs:
LRANGE arq:in_progress 0 -1
LRANGE arq:failed_jobs 0 -1

# Re-queue a failed job (use only when idempotency is confirmed):
LMOVE arq:failed_jobs arq:queue RIGHT LEFT

# Clear dead-letter (when jobs are unrecoverable):
DEL arq:failed_jobs
```

---

## 10. Emergency contacts and escalation

| Severity | Action |
|---|---|
| P0 security breach | Immediately rotate all secrets. Take service offline if data is at risk. |
| P0 data corruption | Stop all writes. Take snapshot. Contact Supabase support. |
| P1 service down | Check logs, rollback if recent deploy, scale if capacity issue. |
| Billing alert fired | Check Cloud Monitoring for cost anomaly. Scale down if runaway. |

---

*Last updated: 2026-10-05*
