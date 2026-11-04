# PRAXIS InterviewOS — Least-Privilege IAM Matrix

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Service Account Inventory

PRAXIS follows the principle of least privilege, assigning dedicated service identities to each architectural component rather than relying on default compute service accounts or broad `Editor`/`Owner` roles:

| Service Account Identity | Component | Granted Roles | Justification |
|---|---|---|---|
| `praxis-api-sa@${PROJECT}.iam.gserviceaccount.com` | `praxis-api` | `roles/secretmanager.secretAccessor`<br>`roles/storage.objectAdmin`<br>`roles/logging.logWriter`<br>`roles/cloudtrace.agent` | Access to database and JWT secrets, resume bucket uploads, structured logging. |
| `praxis-realtime-sa@${PROJECT}.iam.gserviceaccount.com` | `praxis-realtime` | `roles/secretmanager.secretAccessor`<br>`roles/logging.logWriter`<br>`roles/cloudtrace.agent` | Secret Manager read (Redis URL, JWT secret), logging, no direct object storage write. |
| `praxis-worker-sa@${PROJECT}.iam.gserviceaccount.com` | `praxis-worker` | `roles/secretmanager.secretAccessor`<br>`roles/storage.objectAdmin`<br>`roles/logging.logWriter` | Storage access for resume reading/deleting, AI secrets, database secrets. |
| `praxis-sandbox-sa@${PROJECT}.iam.gserviceaccount.com` | `praxis-sandbox` | `roles/logging.logWriter` | **Zero secret access.** Zero storage access. Strictly logging only. |
| `praxis-cloudbuild-sa@${PROJECT}.iam.gserviceaccount.com` | Cloud Build CI/CD | `roles/run.developer`<br>`roles/iam.serviceAccountUser`<br>`roles/artifactregistry.writer` | Builds and deploys containers to Cloud Run using service account impersonation. |

---

## 2. Invariants

1. **No Project-Level Owner/Editor:** No runtime container inherits `roles/editor` or `roles/owner`.
2. **Secret Pinning:** Secret accessor IAM bindings are scoped to specific secret resources (`praxis-database-url`, `praxis-redis-url`, `praxis-jwt-secret`, `praxis-ai-keys`) rather than project-wide secret manager admin.
