# PRAXIS InterviewOS — Disaster Recovery Runbook

**Document ID**: PROD-DR-001  
**Milestone**: Phase 5 — Production Engineering  
**Recovery Targets**: RPO $\le 15\text{ minutes}$ | RTO $\le 60\text{ minutes}$  
**Date**: 2026-11-01  
**Status**: Authoritative Disaster Recovery Runbook  

---

## 1. Disaster Recovery Objectives & SLAs

| Recovery Metric | Target SLA | Implementation Mechanism | Validation Evidence |
| :--- | :---: | :--- | :--- |
| **Recovery Point Objective (RPO)** | **$\le 15\text{ min}$** | Continuous PostgreSQL Write-Ahead Log (WAL) archiving + daily snapshots | Verified via Supabase PITR capability |
| **Recovery Time Objective (RTO)** | **$\le 60\text{ min}$** | Terraform automated infrastructure replay + container image pull | Replay verified in staging deployment |

---

## 2. Step-by-Step Complete Site Restoration Runbook

In the event of a catastrophic regional failure in `asia-south1` or primary database corruption:

```mermaid
sequenceDiagram
    autonumber
    actor SRE as SRE On-Call Lead
    participant Supabase as Database Tier (PITR)
    participant TF as Terraform Orchestrator
    participant Reg as Artifact Registry
    participant DNS as Cloud DNS / CDN

    SRE->>Supabase: Trigger Point-in-Time Recovery (PITR) to T minus 15 min
    Supabase-->>SRE: Restored PostgreSQL connection string emitted
    SRE->>TF: Update region variable (e.g. region = "asia-southeast1")
    SRE->>TF: terraform apply -var="image_tag=LATEST_STABLE_SHA"
    TF->>Reg: Pull immutable images from global registry
    TF-->>SRE: Cloud Run services and VPC connectors provisioned
    SRE->>SRE: Run python scripts/final_quality_gate.py (Verify 15/15)
    SRE->>DNS: Update DNS A/CNAME records to new regional load balancer
    DNS-->>SRE: Global traffic migrated cleanly
```

### Detailed Operational Commands

```bash
# Step 1: Navigate to Terraform production environment
cd infra/gcp/environments/production

# Step 2: In case of regional failure, point to secondary failover region (e.g. asia-southeast1)
terraform apply \
  -var-file=terraform.tfvars \
  -var="region=asia-southeast1" \
  -var="image_tag=0f1e6e5" \
  -auto-approve

# Step 3: Run completeness and security validation against recovered database
uv run python scripts/final_quality_gate.py
uv run python scripts/check_backend_completeness.py
```

---

## 3. Data Deletion & Backup Expiration Compliance

Under GDPR Article 17 ("Right to be Forgotten"):
1. When a candidate requests account deletion, a cryptographic deletion tombstone is recorded.
2. Background worker purges all candidate rows across all 71 tables and deletes S3 resumes.
3. Database backups expire on an automated **30-day retention schedule**, guaranteeing that historical WAL archives naturally age out and permanently eliminate deleted candidate records.
