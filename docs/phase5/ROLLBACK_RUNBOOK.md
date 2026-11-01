# PRAXIS InterviewOS — Production Rollback Runbook

**Document ID**: PROD-ROLLBACK-001  
**Milestone**: Phase 5 — Production Engineering  
**Recovery Target**: MTTR $< 5\text{ minutes}$ for application traffic rollback  
**Date**: 2026-11-01  
**Status**: Authoritative Emergency Operational Runbook  

---

## 1. Rollback Trigger Criteria

An emergency rollback must be initiated immediately if any of the following threshold conditions occur within 30 minutes of a production release:

| Incident Indicator | Alert Trigger Threshold | Severity | Immediate Action |
| :--- | :--- | :---: | :--- |
| **API Error Spike** | 5xx error rate $> 1.0\%$ for 5 minutes | **P1 (Critical)** | Roll back API revision to previous stable SHA |
| **Latency Degradation**| p95 latency $> 3,000\text{ ms}$ for 5 minutes | **P2 (High)** | Roll back API revision to previous stable SHA |
| **Container Crash Loop**| Instance crash count $> 0$ | **P1 (Critical)** | Roll back crashing container revision |
| **Realtime Failure** | WebSocket connection failure $> 5.0\%$ | **P1 (Critical)** | Roll back `praxis-realtime` revision |
| **Data Integrity Alert**| Unhandled database migration error | **P1 (Critical)** | Halt traffic, isolate database, invoke SRE Lead |

---

## 2. Emergency Rollback Procedures

### 2.1 Fast Traffic Reversion via Google Cloud CLI (< 60 Seconds)
Cloud Run maintains all previous container revisions in an idle state. Traffic can be redirected instantly to the known good revision without rebuilding or redeploying:

```bash
# 1. Identify previous healthy revision
gcloud run revisions list \
  --service=praxis-api \
  --region=asia-south1 \
  --project=praxis-production \
  --limit=5

# 2. Re-route 100% of traffic immediately to previous revision
gcloud run services update-traffic praxis-api \
  --region=asia-south1 \
  --project=praxis-production \
  --to-revisions=praxis-api-PREVIOUS_STABLE_REVISION=100

# 3. Repeat for realtime service if affected
gcloud run services update-traffic praxis-realtime \
  --region=asia-south1 \
  --project=praxis-production \
  --to-revisions=praxis-realtime-PREVIOUS_STABLE_REVISION=100
```

### 2.2 Reverting Infrastructure State via Terraform (< 5 Minutes)
```bash
cd infra/gcp/environments/production

# Apply Terraform pointing to previous stable Git SHA
terraform apply \
  -var-file=terraform.tfvars \
  -var="image_tag=PREVIOUS_STABLE_SHA" \
  -auto-approve
```

---

## 3. Database Migration Rollback Safety

> [!CAUTION]
> Reverting a container image does NOT automatically reverse database schema changes. Reversing a database migration requires explicit safety checks.

### Safe Rollback Matrix
1. **Additive Changes (Expand Phase)**:  
   New nullable columns, new tables, or new indexes do not break older container revisions. Reverting the application container image is **100% safe** while leaving the database schema as-is.
2. **Destructive Changes (Contract Phase)**:  
   If a migration dropped a column or table, restoring requires point-in-time recovery (PITR) from the automated Supabase backup snapshot. Do **not** run destructive rollback scripts without taking an immediate manual snapshot first.

---

## 4. Post-Rollback Escalation & Incident Review

1. **Incident Notification**: Post update to `#engineering-incidents` channel within 10 minutes of rollback.
2. **Log & Trace Preservation**: Export Cloud Logging query results covering the incident window with correlation IDs for root cause analysis.
3. **Blameless Post-Mortem**: Convene within 24 hours to document root cause, timeline, impact, and preventive regression tests.
