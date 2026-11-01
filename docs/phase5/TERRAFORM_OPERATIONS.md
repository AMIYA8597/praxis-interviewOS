# PRAXIS InterviewOS — Terraform Operational Runbook

**Document ID**: PROD-TF-OPS-001  
**Milestone**: Phase 5 — Production Engineering  
**Terraform Version**: `>= 1.9.0` (Google Provider `~> 6.14`)  
**State Backend**: Google Cloud Storage (`gcs`)  
**Date**: 2026-11-01  
**Status**: Authoritative Operational Runbook  

---

## 1. Remote State & Bootstrap Hierarchy

Infrastructure provisioning follows a strict 2-step hierarchy:
1. **Bootstrap Phase (`infra/bootstrap/`)**:  
   Provisions the encrypted Google Cloud Storage (GCS) bucket with object versioning and uniform bucket-level access to store the Terraform state files.
2. **Environment Execution Phase (`infra/gcp/environments/{env}/`)**:  
   Initializes the remote backend against the state bucket and provisions the Cloud Run services, VPC connector, Redis instance, Secret Manager references, and monitoring alerts.

```
infra/
├── bootstrap/
│   ├── main.tf             # GCS state bucket definition (praxis-tfstate)
│   └── .terraform.lock.hcl
└── gcp/
    ├── main.tf             # Core infrastructure modules
    ├── alerting.tf         # Cloud Monitoring alert policies
    └── environments/
        ├── staging/
        │   ├── backend.conf
        │   └── terraform.tfvars
        └── production/
            ├── backend.conf
            └── terraform.tfvars
```

---

## 2. Standard Terraform Operational Lifecycle

### 2.1 Initialization
```bash
# Navigate to desired environment (e.g. staging)
cd infra/gcp/environments/staging

# Initialize backend using remote configuration
terraform init -backend-config=backend.conf
```

### 2.2 Planning (Dry Run)
```bash
# Generate deterministic execution plan with image tag pinned to Git SHA
terraform plan \
  -var-file=terraform.tfvars \
  -var="image_tag=0f1e6e5" \
  -out=staging.tfplan
```

### 2.3 Application (Controlled & Logged)
> [!IMPORTANT]
> Automatic destruction or unreviewed applies in production are strictly forbidden. An engineer must inspect the plan output before applying.

```bash
# Apply verified plan
terraform apply staging.tfplan
```

---

## 3. Safe Rollback & Failure Recovery

### 3.1 Reverting to Previous Container Revision
If a newly deployed image tag introduces a regression:
```bash
# Re-apply Terraform pointing to previous stable Git SHA
terraform apply \
  -var-file=terraform.tfvars \
  -var="image_tag=PREVIOUS_STABLE_SHA" \
  -auto-approve
```
Cloud Run automatically migrates 100% of traffic back to the previous healthy revision within 5–10 seconds without dropping active connections.

### 3.2 State Lock Recovery
If an interrupted plan or network disconnect leaves a state lock on GCS:
```bash
# Inspect the lock ID in the error output
terraform force-unlock <LOCK_ID>
```
*(Only execute after verifying that no concurrent CI/CD pipeline or engineer is running an active apply).*
