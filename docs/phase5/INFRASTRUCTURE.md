# PRAXIS InterviewOS — Infrastructure as Code & GCP Operations

**Document ID**: PROD-INFRA-001  
**Milestone**: Phase 5 — Production Engineering & Infrastructure  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Infrastructure Architecture & Terraform Specification  

---

## 1. Google Cloud Resource Inventory

All cloud infrastructure is provisioned through modular Terraform code targeting the primary production region: **`asia-south1` (Mumbai)**.

| Resource Name | GCP Type | Purpose | Configuration / Capacity |
| :--- | :--- | :--- | :--- |
| **`praxis-vpc`** | `google_compute_network` | Isolated VPC Network | Custom subnet mode, private Google access enabled |
| **`praxis-subnet`** | `google_compute_subnetwork` | Main private subnet | Primary CIDR: `10.0.0.0/24` in `asia-south1` |
| **`praxis-vpc-connector`** | `google_vpc_access_connector` | Serverless VPC Access | CIDR: `10.0.0.0/28`, min 2, max 10 throughput instances |
| **`praxis-redis`** | `google_redis_instance` | Memorystore Redis 7 | Basic Tier, 1 GiB (Staging) / 2 GiB (Prod), bound to `10.0.0.4:6379` |
| **`praxis-containers`** | `google_artifact_registry_repository` | Container Registry | Format: DOCKER, regional immutable digest repository |
| **`praxis-api`** | `google_cloud_run_v2_service` | Core REST API | 2 vCPU, 2 GiB, Direct VPC egress, autoscale 1–10 instances |
| **`praxis-realtime`** | `google_cloud_run_v2_service` | Realtime Speech Gateway | 4 vCPU, 4 GiB, Session Affinity = true, autoscale 1–5 instances |
| **`praxis-worker`** | `google_cloud_run_v2_service` | ARQ Background Workers | 2 vCPU, 2 GiB, Direct VPC egress, fixed 1–4 instances, probe :8080 |
| **`praxis-secrets`** | `google_secret_manager_secret` | Encrypted Secrets Vault | Automatic replication, version pinned, zero plaintext in code |
| **`praxis-lb`** | `google_compute_global_forwarding_rule` | Global HTTPS/WSS LB | SSL termination, Cloud Armor WAF integration |

---

## 2. Terraform Module Architecture

```text
infra/
├── bootstrap/                      # State bucket & KMS key bootstrapping
│   └── main.tf                     # GCS bucket with object versioning & encryption
├── gcp/                            # Core resource definitions (1155 lines)
│   ├── main.tf                     # Cloud Run, VPC, Redis, Artifact Registry, Secrets
│   ├── alerting.tf                 # Cloud Monitoring alert policies & metrics
│   └── environments/               # Environment variable definitions
│       ├── staging/terraform.tfvars
│       └── production/terraform.tfvars
└── terraform/                      # Root orchestration module
    ├── main.tf                     # Module wrapper invoking ../gcp
    ├── variables.tf                # Parameter declarations
    ├── outputs.tf                  # Exported IPs, URLs, and WIF names
    └── environments/               # Sizing profiles (staging vs production)
```

### Module Verification Evidence
Both modules have been validated using HashiCorp Terraform `~> 6.14`:
- `cd infra/gcp && terraform validate`: **PASS (Success! The configuration is valid.)**
- `cd infra/terraform && terraform validate`: **PASS (Success! The configuration is valid.)**

---

## 3. IAM & Service Account Security

Every service operates under a dedicated, least-privilege service account:

```text
1. sa-praxis-api@praxis-production.iam.gserviceaccount.com
   - roles/secretmanager.secretAccessor (read-only for pinned secrets)
   - roles/vpcaccess.user (egress through serverless connector)

2. sa-praxis-realtime@praxis-production.iam.gserviceaccount.com
   - roles/secretmanager.secretAccessor
   - roles/vpcaccess.user

3. sa-praxis-worker@praxis-production.iam.gserviceaccount.com
   - roles/secretmanager.secretAccessor
   - roles/vpcaccess.user

4. sa-praxis-deployer@praxis-production.iam.gserviceaccount.com
   - roles/run.developer (deploy revisions)
   - roles/artifactregistry.writer (push images)
   - Bound via Workload Identity Federation (WIF) — Zero JSON Service Account Keys stored in Git!
```

---

## 4. Staging vs. Production Sizing Profiles

| Configuration Parameter | Staging Profile (`environments/staging`) | Production Profile (`environments/production`) |
| :--- | :--- | :--- |
| **GCP Project ID** | `praxis-staging` (Isolated Project) | `praxis-production` (Isolated Project) |
| **API Autoscaling** | 0 to 3 instances (Scale-to-Zero enabled) | 1 to 10 instances (Min: 1 Warm Instance) |
| **Realtime Autoscaling** | 1 to 2 instances (Min: 1 for cold-start VAD) | 1 to 5 instances (Min: 1 Warm Instance) |
| **Worker Compute** | 1 instance (Scale-to-Zero worker disabled) | 2 instances (Redundant background processing) |
| **Memorystore Redis** | 1 GiB Basic Tier | 2 GiB Basic Tier |
| **Secret Versioning** | Pinned version `"1"` | Pinned version `"1"` |
| **Image Tagging** | Branch SHA: `staging-${SHORT_SHA}` | Immutable Digest: `sha256:...` |
| **Domain & TLS** | Direct Cloud Run HTTPS | Custom Domain with Google-Managed SSL |

---

## 5. Terraform Operations Runbook

### Remote State Management
State is persisted in a protected Google Cloud Storage bucket with object versioning:
```bash
# Initialize Terraform with backend configuration
terraform init -backend-config="bucket=praxis-tfstate-production" -backend-config="prefix=terraform/state"
```

### Plan & Review
```bash
# Execute dry-run plan
terraform plan -var-file=environments/production/terraform.tfvars -out=tfplan.binary
```

### Apply Plan (Production Gate)
```bash
# Explicit human approval required before execution
terraform apply tfplan.binary
```
