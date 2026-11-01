# PRAXIS InterviewOS — Security Logging, Monitoring & Observability Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: AUDIT & OBSERVABILITY SPECIFICATION  

---

## 1. Security Event Logging Architecture

PRAXIS utilizes structured JSON logging (`backend/app/core/logging_config.py`) integrated with OpenTelemetry tracing:

```json
{
  "timestamp": "2026-11-01T10:55:00.123Z",
  "level": "WARNING",
  "event": "jwt_rejected",
  "reason": "expired",
  "request_id": "8f3b2e1a-4d2c-...",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "client_ip": "198.51.100.42"
}
```

---

## 2. PII & Secret Redaction Invariants

1. **Zero Credential Printing**:
   - `Authorization` header bearer tokens are NEVER logged.
   - Passwords, refresh tokens, and AI provider API keys are stripped before log formatting.
2. **Document & Speech Redaction**:
   - Full resume text and raw audio waveforms are omitted from operational logs.
   - Only document IDs and chunk counts are logged.

---

## 3. High-Priority Alert Triggers

| Alert Identifier | Threshold / Condition | Severity | Automated Action |
| :--- | :--- | :--- | :--- |
| `SEC-ALERT-01` | >= 10 JWT validation failures in 1 minute from single IP | Medium | Temporary IP rate limit cooldown |
| `SEC-ALERT-02` | Unauthorized attempt to access cross-tenant session | High | Security team alert; session flagged |
| `SEC-ALERT-03` | Prompt injection pattern detected in resume parsing | Medium | Content quarantined; evaluated under strict sandbox |
| `SEC-ALERT-04` | AI Gateway circuit breaker trips (5 consecutive errors)| High | Automatic failover to secondary provider |
