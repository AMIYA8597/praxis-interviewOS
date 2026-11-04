# PRAXIS InterviewOS — Incident Response & Operational Runbook

**Document Version:** 1.0.0  
**Target Operations:** SRE, On-Call Engineers, Platform Administrators  
**Severity Levels:** SEV-1 (Critical Outage), SEV-2 (Degraded Experience), SEV-3 (Minor / Informational)

---

## 1. Incident Severity Definitions & Response SLAs

| Severity | Definition & Impact | Response SLA | Target Resolution | Escalation Path |
|---|---|---|---|---|
| **SEV-1 (Critical)** | Core API unavailable, database unreachable, or WebSocket connections completely failing across all candidates. | `< 15 minutes` | `< 1 hour` | Lead Infrastructure Engineer + Security Officer |
| **SEV-2 (Degraded)** | Third-party LLM outage causing Realtime sessions to drop to `DSP_ONLY` mode; background worker queue processing delayed > 5 minutes. | `< 30 minutes` | `< 4 hours` | Backend On-Call Engineer |
| **SEV-3 (Minor)** | Isolated candidate code execution sandbox timeout; rate limit burst spikes; non-critical dashboard telemetry delay. | `< 2 hours` | `< 24 hours` | Application Developer |

---

## 2. P1 Diagnostic Procedures & Playbooks

### Playbook 1: PostgreSQL Connection Pool Saturation
- **Symptom:** API returns `503 Service Unavailable` on `/health/ready`; logs contain `asyncpg.exceptions.TooManyConnectionsError` or pool checkout timeouts.
- **Diagnostic Commands:**
  ```bash
  # Check active connection count by database role
  psql -h $PGHOST -U postgres -d praxis -c "SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;"
  
  # Check longest running active queries
  psql -h $PGHOST -U postgres -d praxis -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;"
  ```
- **Remediation:**
  1. Terminate orphaned backend query connections:
     ```sql
     SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > interval '30 seconds' AND usename = 'praxis_app';
     ```
  2. If Cloud Run autoscaling spawned excessive instances, lower `max_instances` in `infra/gcp/main.tf` or adjust Cloud SQL connection pool budget.

### Playbook 2: All AI Providers Tripped (Realtime in `DSP_ONLY` Mode)
- **Symptom:** WebSocket clients receive `session.degraded` with `AI_ALL_PROVIDERS_UNAVAILABLE`. Realtime transcripts record speech but no interviewer questions are generated.
- **Diagnostic Commands:**
  ```bash
  # Probe provider endpoint health directly from API container
  curl -fsS https://api.praxis.internal/health/providers
  ```
- **Remediation:**
  1. Inspect response: identify which provider is in `circuit_breaker_state: OPEN`.
  2. Check upstream status dashboards (status.groq.com, status.openai.com, anthropic status).
  3. If API keys were revoked or exhausted:
     - Update Secret Manager secret: `gcloud secrets versions add ai-provider-keys --data-file=new_keys.json`
     - Restart Cloud Run revisions to consume new secrets.
  4. Note: Candidates can continue practice; speech coaching HUD remains fully operational.

### Playbook 3: ARQ Worker Queue Backlog & Dead-Letter Buildup
- **Symptom:** Resume uploads stuck in `parsing` status; `failed_jobs` table row count increasing.
- **Diagnostic Commands:**
  ```bash
  # Check pending jobs in Redis
  redis-cli -u $REDIS_URL LLEN arq:queue
  
  # Query failed jobs from authoritative database
  psql -h $PGHOST -U praxis -d praxis -c "SELECT id, job_name, error, failed_at FROM failed_jobs ORDER BY failed_at DESC LIMIT 10;"
  ```
- **Remediation:**
  1. Scale worker service: `gcloud run services update praxis-worker --min-instances 3 --max-instances 10`
  2. Inspect `failed_jobs.error` for poison pill payloads (e.g. malformed PDF crashing PDF parser).
  3. Replay failed jobs after defect resolution using `python scripts/requeue_failed_jobs.py`.

---

## 3. Privacy, Masking & Log Sanitization Mandate

To protect candidate privacy and comply with GDPR / CCPA:
- **Never Log Plaintext Credentials:** Bearer tokens, JWT strings, `OPENAI_API_KEY`, database passwords, or Redis URLs must never appear in log payloads or Cloud Trace spans.
- **Never Log Raw Resumes or Private Contact Info:** Email addresses, phone numbers, and physical addresses must be masked (`a***@domain.com`).
- **Audit Log Integrity:** All security events (permission rejections, admin actions, export downloads) are written to the append-only `audit_logs` table with verified request correlation IDs.
