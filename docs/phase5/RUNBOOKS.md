# PRAXIS InterviewOS — Production Operational Runbooks

**Document ID**: PROD-RUNBOOK-001  
**Milestone**: Phase 5 — Production SRE & Operational Runbooks  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Standard Operating Procedures & Disaster Runbooks  

---

## Runbook 1: Cloud Run Emergency Rollback (MTTR < 60s)

### When to Execute
- Error rate $> 2.0\%$ immediately following a production deployment.
- High latency spike (P95 $> 2000\text{ ms}$).
- Unhandled application crash loops.

### Execution Procedure
```bash
# 1. Identify previous healthy revision
gcloud run revisions list --service=praxis-api --region=asia-south1 --limit=5

# 2. Instantly redirect 100% traffic to previous golden revision
gcloud run services update-traffic praxis-api \
  --to-revisions=praxis-api-GOLDEN_REV=100 \
  --region=asia-south1

# 3. Roll back Realtime Gateway if affected
gcloud run services update-traffic praxis-realtime \
  --to-revisions=praxis-realtime-GOLDEN_REV=100 \
  --region=asia-south1

# 4. Verify traffic cutover
gcloud run services describe praxis-api --region=asia-south1 --format="value(status.traffic)"
```

---

## Runbook 2: Database Connection Starvation Mitigation

### Symptoms
- Log message: `sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 3 reached`.
- Cloud Monitoring alert: `praxis_db_pool_active_connections > 4`.

### Triage & Remediation
1. **Inspect Active Connections in PostgreSQL**:
   ```sql
   SELECT count(*), state, application_name 
   FROM pg_stat_activity 
   WHERE datname = 'praxis' 
   GROUP BY state, application_name;
   ```
2. **Terminate Stale Idle Connections**:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE datname = 'praxis' 
     AND state = 'idle in transaction' 
     AND state_change < now() - INTERVAL '5 minutes';
   ```
3. **Verify Per-Container Settings**:
   Ensure Cloud Run instances have not exceeded their 5-connection ceiling (`DB_POOL_SIZE = 2, DB_MAX_OVERFLOW = 3`).

---

## Runbook 3: Redis Queue Backlog & Worker Scaling

### Symptoms
- Alert: `praxis_redis_queue_depth > 50`.
- Document parsing or debrief scoring jobs delayed $> 5\text{ minutes}$.

### Remediation
1. **Check Worker Instance Status**:
   ```bash
   gcloud run services describe praxis-worker --region=asia-south1
   ```
2. **Scale Worker Instances**:
   ```bash
   # Temporarily increase worker instance count to drain backlog
   gcloud run services update praxis-worker \
     --min-instances=4 \
     --max-instances=8 \
     --region=asia-south1
   ```
3. **Inspect Failed Jobs Queue in Redis**:
   ```bash
   redis-cli -h 10.0.0.4 -p 6379 LLEN arq:queue
   ```

---

## Runbook 4: AI Provider Outage & Manual Fallback Trigger

### Symptoms
- OpenAI API returns HTTP 500 / 503 or latency exceeds 10.0 seconds.
- AI Gateway circuit breaker tripped (`praxis_ai_provider_circuit_breaker = 1`).

### Remediation
1. **Verify Automated Fallback**:
   The AI Gateway automatically routes traffic to Gemini or DeepSeek upon 5 consecutive failures.
2. **Force Manual Provider Switch (via Secret Manager or Environment Variable)**:
   ```bash
   # Update runtime configuration to bypass OpenAI entirely
   gcloud run services update praxis-api \
     --update-env-vars=LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-1.5-pro \
     --region=asia-south1
   ```

---

## Runbook 5: Zero-Downtime Secret Rotation

### Frequency
- Scheduled rotation: Every 90 days.
- Emergency rotation: Immediate upon suspected credential compromise.

### Rotation Steps (Example: Supabase Service Role Key)
1. **Generate New Secret in Supabase Console**.
2. **Add New Version to Secret Manager**:
   ```bash
   echo -n "NEW_SECRET_VALUE" | gcloud secrets versions add SUPABASE_SERVICE_ROLE_KEY --data-file=-
   ```
3. **Update Terraform Secret Version Pointer**:
   Update `secret_version = "2"` in `environments/production/terraform.tfvars`.
4. **Deploy Application Revision**:
   Apply Terraform plan; Cloud Run performs zero-downtime rolling replacement of container instances.
5. **Revoke Old Secret** after 24 hours of stable execution.
