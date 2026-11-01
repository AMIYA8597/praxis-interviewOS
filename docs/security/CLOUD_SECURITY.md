# PRAXIS InterviewOS — Google Cloud Infrastructure Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: CLOUD SECURITY AUDIT & SPECIFICATION  

---

## 1. Cloud Architecture & Infrastructure as Code (Terraform)

PRAXIS deploys on Google Cloud Platform (region: `asia-south1`) managed via declarative Terraform configuration in `infra/gcp/main.tf`:
- **Serverless Compute**: Cloud Run v2 (Dedicated services: `api`, `realtime-agent`, `worker`).
- **Private Networking**: Serverless VPC Access connector (`10.8.0.0/28`) bridging Cloud Run to private Memorystore Redis and Cloud SQL.
- **Secrets Management**: Cloud Secret Manager with IAM role bindings.
- **Container Registry**: Google Artifact Registry with vulnerability scanning enabled.

---

## 2. Infrastructure Invariants & Hardening

1. **Ingress Restrictions**:
   - `realtime-agent` and `api` allow authenticated public ingress via Cloud Armor HTTPS load balancers.
   - `worker` service is configured with `ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"`, preventing direct internet access.
2. **Container Security**:
   - Containers run as non-root unprivileged users (`nobody` or dedicated service UID).
   - Execution environment root filesystem mounted read-only where applicable.
3. **Automated CI Deployment Authentication**:
   - GitHub Actions authenticates using **Workload Identity Federation (WIF)**, eliminating the risk of leaked long-lived service account JSON key files.
