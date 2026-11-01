# PRAXIS InterviewOS — Incident Response Plan

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: INCIDENT RESPONSE & RUNBOOK  

---

## 1. Incident Severity Definitions

- **SEV-1 (Critical)**: Active cross-tenant data leak, remote code execution in sandbox, or exposed root/service-role credentials. Immediate response: < 15 minutes.
- **SEV-2 (High)**: AI Gateway provider key compromised, persistent WebSocket denial of service, or elevated auth failure rates. Immediate response: < 1 hour.
- **SEV-3 (Medium)**: Isolated rate limit bypass, dependency vulnerability report without known exploit. Response: < 24 hours.

---

## 2. Six-Phase Response Workflow

```
[ Phase 1: Detection & Triage ]
  - Ingestion via Cloud Monitoring alerts, Sentry error spikes, or bug reports.
  - Triage severity (SEV-1 to SEV-3) and assign Incident Commander.

[ Phase 2: Containment ]
  - If credential compromised: Immediately rotate secret via GCP Secret Manager.
  - If IP flooding: Block IP range in Cloud Armor / WAF rules.
  - If malicious session: Revoke session token and sever WebSocket connections.

[ Phase 3: Evidence Preservation ]
  - Snapshot Cloud SQL database and relevant audit log partitions.
  - Export structured JSON logs and Cloud Trace traces for root-cause forensic analysis.

[ Phase 4: Eradication & Remediation ]
  - Patch confirmed code vulnerability; author automated regression test.
  - Deploy emergency hotfix through CI/CD pipeline.

[ Phase 5: Recovery & Verification ]
  - Verify services pass all automated quality gates and security test suites.
  - Monitor error rates and traffic patterns for 2 hours post-recovery.

[ Phase 6: Post-Mortem & Prevention ]
  - Author blameless post-mortem report within 48 hours.
  - Update Threat Model (`THREAT_MODEL.md`) and regression test suites.
```
