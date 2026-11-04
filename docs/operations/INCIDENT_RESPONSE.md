# PRAXIS InterviewOS — Incident Response & Triage Playbook

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Severity Classification Standard:** SEV-1 (Critical) to SEV-3 (Low)  

---

## 1. Severity Levels & Escalation Criteria

| Severity | Definition | Target Response (MTTD / MTTR) | Escalation Channel | Example Trigger |
|---|---|---|---|---|
| **SEV-1 (Critical)** | Core interview streaming down; cross-tenant data leak; database offline; secret compromise. | MTTD: < 2 min<br>MTTR: < 15 min | PagerDuty + Immediate On-Call Engineer | Realtime WebSocket handshake failure rate > 5%; Database pool exhaustion. |
| **SEV-2 (Major)** | AI provider outage; degraded scoring mode active; worker queue backlog > 100 jobs. | MTTD: < 5 min<br>MTTR: < 30 min | Slack `#ops-alerts` + Primary Engineer | Upstream LLM returns 5xx; circuit breaker trips to `OPEN`. |
| **SEV-3 (Minor)** | Non-blocking metric warning; slow query (> 500ms); rate limit false positives. | MTTD: < 15 min<br>MTTR: < 4 hours | Jira / GitHub Issue Tracking | Minor increase in client retry rate. |

---

## 2. Standard Triage Playbooks

### Playbook A — AI Provider Outage & Circuit Breaker Trip
1. **Detection:** Cloud Monitoring alert `praxis-ai-provider-circuit-breaker-open` fires.
2. **Diagnostic:** Call `GET /api/v1/observability/provider-health` to inspect failure states and retry-after headers.
3. **Mitigation:**
   - The AI Gateway automatically fails over to the next candidate model in `config/models.yaml` (e.g. Gemini -> OpenAI -> Anthropic).
   - If all cloud providers fail, the system enters degraded mode, queuing debrief evaluations for background replay without fabricating data.
4. **Resolution:** Check provider status page; once healthy, the circuit breaker resets to `HALF_OPEN` and resumes traffic.

### Playbook B — Database Pool Saturation
1. **Detection:** `DBPoolSaturationAlert` fires when active connections reach 85% of pool limit.
2. **Diagnostic:** Inspect active connections in PostgreSQL:
   ```sql
   SELECT pid, state, query, age(clock_timestamp(), query_start) 
   FROM pg_stat_activity 
   WHERE state != 'idle' ORDER BY age DESC;
   ```
3. **Mitigation:**
   - Cancel long-running queries (> 30s) automatically via `statement_timeout`.
   - Scale down idle background workers if consuming excess pooled connections.

### Playbook C — Realtime WebSocket Disconnect Spike
1. **Detection:** Elevated reconnect rate detected in `realtime_agent` metrics.
2. **Diagnostic:** Review Cloud Run instance logs for crash loops or memory saturation.
3. **Mitigation:** Transparent TCP reconnection resumes active sessions within 30s using Redis state. If instance crashed, Cloud Run spins up replacement and session resumes from Redis.
