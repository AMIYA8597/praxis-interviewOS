# PRAXIS InterviewOS — Google Cloud Deployment Prerequisites & Readiness

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Audit Status:** Empirical Discovery Verified  

---

## 1. Verified Live Discovery State

| Attribute | Detected Value | Verification Method | Status |
|---|---|---|:---:|
| **Authenticated Google Account** | `amiyachowdhury04@gmail.com` | `gcloud auth list` | **PASS** |
| **Billing Account ID** | `01DE13-945CB6-4911D1` ("My Billing Account") | `gcloud billing accounts list` | **PASS** (Open: True) |
| **Current Default Project** | `tradebit-396406` | `gcloud config list` | **ACTIVE** |
| **Staging Target Project** | `praxis-staging` (or dedicated staging ID) | `gcloud projects list` | **BLOCKED** (Not yet created) |
| **Target Cloud Region** | `asia-south1` (Mumbai) | `infra/gcp/environments/staging/terraform.tfvars` | **CONFIGURED** |
| **Terraform Version** | `v1.16.4` (windows_amd64) | `terraform --version` | **PASS** |
| **Google Cloud SDK** | `587.0.0` (core, gsutil, bq) | `gcloud --version` | **PASS** |
| **Docker Engine** | `29.7.2` (build `a7dcaa6`) | `docker --version` | **PASS** |

---

## 2. Required GCP API Inventory

The following 14 Google Cloud APIs are required for PRAXIS backend staging:
1. `run.googleapis.com` (Cloud Run Admin API)
2. `cloudbuild.googleapis.com` (Cloud Build API)
3. `artifactregistry.googleapis.com` (Artifact Registry API)
4. `secretmanager.googleapis.com` (Secret Manager API)
5. `storage.googleapis.com` (Cloud Storage API)
6. `redis.googleapis.com` (Google Cloud Memorystore for Redis API)
7. `vpcaccess.googleapis.com` (Serverless VPC Access API)
8. `compute.googleapis.com` (Compute Engine API for VPC networking)
9. `iam.googleapis.com` (Identity and Access Management API)
10. `iamcredentials.googleapis.com` (IAM Service Account Credentials API)
11. `monitoring.googleapis.com` (Cloud Monitoring API)
12. `logging.googleapis.com` (Cloud Logging API)
13. `cloudscheduler.googleapis.com` (Cloud Scheduler API)
14. `cloudtrace.googleapis.com` (Cloud Trace API)

---

## 3. Prerequisite Setup Instructions (Execution Barrier)

In accordance with Rule 0.2:
- *"Do not apply Terraform, create chargeable infrastructure, incur material cloud expenditure, destroy resources or rotate production credentials without explicit authorization."*

To authorize project creation:
```bash
# 1. Create staging project
gcloud projects create praxis-staging --name="PRAXIS Staging"

# 2. Link billing account
gcloud billing projects link praxis-staging --billing-account=01DE13-945CB6-4911D1

# 3. Enable required core APIs
gcloud services enable --project=praxis-staging \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```
