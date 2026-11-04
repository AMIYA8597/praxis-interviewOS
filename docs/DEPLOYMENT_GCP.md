# PRAXIS InterviewOS — Google Cloud Deployment Guide

**Deployment Target:** Google Cloud Platform (GCP)  
**IaC Toolchain:** Terraform 1.5+ with HashiCorp Google Provider `~> 6.50.0`  
**Container Engine:** Cloud Build & Artifact Registry  
**Serverless Runtime:** Cloud Run (2nd Generation Execution Environment)  

---

## 1. Prerequisites & Toolchain Verification

Before deploying to GCP, verify the following prerequisites on your administrative workstation or CI runner:

```bash
# 1. Verify Google Cloud SDK and Terraform versions
gcloud --version
terraform -version

# 2. Authenticate administrative session
gcloud auth login
gcloud auth application-default login

# 3. Configure target GCP project
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

---

## 2. Infrastructure as Code (Terraform) Setup

The Terraform modules are organized into environment overlays:
- `infra/gcp/` (Core infrastructure definitions: Cloud Run, Cloud SQL, Redis, IAM)
- `infra/gcp/environments/staging/` (Staging variables and GCS state backend)
- `infra/gcp/environments/production/` (Production variables and GCS state backend)

### Step 1: Initialize Terraform State Backend
```bash
cd infra/gcp/environments/staging

# Initialize remote state in Google Cloud Storage
terraform init -backend-config=backend.conf
```

### Step 2: Review Terraform Plan
```bash
terraform plan -var-file=terraform.tfvars -out=staging.tfplan
```
Review the planned additions:
- Google Cloud VPC Network & Direct VPC Connector
- Cloud SQL PostgreSQL 17 Instance (`db-custom-2-7680`)
- Memorystore Redis Instance (`redis-1`)
- Secret Manager secrets (`database-url`, `jwt-secret`, `ai-provider-keys`)
- Cloud Run service definitions (`praxis-api`, `praxis-realtime`, `praxis-worker`, `praxis-sandbox`)
- Cloud Monitoring alert policies (`infra/gcp/alerting.tf`)

### Step 3: Apply Infrastructure (Authorized Execution)
```bash
terraform apply staging.tfplan
```

---

## 3. Container Build & Release Pipeline (`cloudbuild.yaml`)

PRAXIS builds all 4 production container images in parallel via Google Cloud Build using immutable commit hashes:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_REGION="asia-south1",_REGISTRY_PROJECT="<YOUR_GCP_PROJECT_ID>"
```

### Build Artifacts Emitted:
1. `asia-south1-docker.pkg.dev/<PROJECT_ID>/praxis/api:<SHORT_SHA>`
2. `asia-south1-docker.pkg.dev/<PROJECT_ID>/praxis/realtime:<SHORT_SHA>`
3. `asia-south1-docker.pkg.dev/<PROJECT_ID>/praxis/worker:<SHORT_SHA>`
4. `asia-south1-docker.pkg.dev/<PROJECT_ID>/praxis/sandbox:<SHORT_SHA>`

---

## 4. Database Migrations Execution on Cloud SQL

Database migrations are executed from a secure Cloud Build bastion or Cloud Run job:

```bash
gcloud run jobs create praxis-migrate \
  --image="asia-south1-docker.pkg.dev/<PROJECT_ID>/praxis/api:<SHORT_SHA>" \
  --command="python" \
  --args="scripts/migrate.py" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --network="praxis-vpc" \
  --subnet="praxis-subnet" \
  --region="asia-south1"

gcloud run jobs execute praxis-migrate --region="asia-south1" --wait
```

---

## 5. Post-Deployment Smoke Test & Gate Verification

Verify that all deployed services are operational:

```bash
# 1. API Liveness Probe
curl -fsS https://api.praxis.internal/health/live

# 2. Database & Migrations Startup Probe
curl -fsS https://api.praxis.internal/health/startup

# 3. AI Provider Circuit Breaker Probe
curl -fsS https://api.praxis.internal/health/providers

# 4. Realtime Agent Readiness Probe
curl -fsS https://realtime.praxis.internal/health/ready
```
All probes must return HTTP 200 OK with `status: "ok"` or `status: "ready"`.
