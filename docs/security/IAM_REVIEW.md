# PRAXIS InterviewOS — IAM Privilege & Role Separation Review

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: IAM AUDIT & LEAST-PRIVILEGE REVIEW  

---

## 1. Service Account Role Scoping

Every cloud workload is assigned a dedicated service account with least-privilege IAM bindings:

| Service Account | Assigned GCP Roles | Justification / Boundary |
| :--- | :--- | :--- |
| `sa-api` | `roles/secretmanager.secretAccessor`<br>`roles/cloudtrace.agent` | Access application secrets and emit telemetry; no administrative privileges |
| `sa-realtime` | `roles/secretmanager.secretAccessor`<br>`roles/cloudtrace.agent` | Realtime agent speech processing and Redis state; isolated from storage deletion |
| `sa-worker` | `roles/secretmanager.secretAccessor`<br>`roles/cloudtrace.agent`<br>`roles/storage.objectAdmin` | Executes asynchronous resume parsing and GDPR deletion cascades |
| `sa-deployer` | `roles/run.developer`<br>`roles/artifactregistry.writer`<br>`roles/iam.serviceAccountUser` | CI/CD pipeline deployer authorized strictly via Workload Identity Federation |

---

## 2. Overly Permissive Role Prohibitions
- `roles/owner` and `roles/editor` are strictly prohibited on service accounts.
- Cross-project IAM impersonation is disabled.
- Default Compute Engine service accounts are disabled / unattached.
