# PRAXIS Staging Prerequisites

This document lists every external resource and credential required before the staging deployment can be executed.

**Detected automatically in this session:**
- gcloud authenticated: `amiyachowdhury04@gmail.com`
- gcloud project: `tradebit-396406`
- Docker: 29.7.2
- Terraform: 1.16.4
- Python: 3.13.7
- Node: 24.18.0
- pnpm: 10.30.3
- Supabase CLI: NOT INSTALLED → `winget install Supabase.CLI`

---

## Prerequisites Table

| Variable | Purpose | Where to Obtain | Secret | Required For | Example Format | Current Status |
|---|---|---|---|---|---|---|
| `GCP_STAGING_PROJECT_ID` | GCP project for staging Cloud Run, Redis, IAM | `gcloud projects create praxis-staging` | No | All GCP resources | `praxis-staging` | **BLOCKED** — project does not exist |
| `GCP_PRODUCTION_PROJECT_ID` | GCP project for production | Same as above | No | Production deployment | `praxis-production` | **BLOCKED** — not created yet; do not create until staging certified |
| `GCP_BILLING_ACCOUNT_ID` | Billing account to link to new project | [GCP Billing Console](https://console.cloud.google.com/billing) | No | Project creation | `012345-ABCDEF-789012` | **BLOCKED** — must confirm billing account |
| `SUPABASE_STAGING_PROJECT_REF` | Supabase staging project | [supabase.com/dashboard](https://supabase.com/dashboard) → New Project | No | DB/Auth | `abcdefghijklmnop` | **BLOCKED** — not created |
| `SUPABASE_STAGING_URL` | Supabase staging API URL | Dashboard → Settings → API | No | Backend config | `https://xxx.supabase.co` | **BLOCKED** |
| `SUPABASE_STAGING_ANON_KEY` | Supabase staging anon key | Dashboard → Settings → API | **YES — Secret Manager** | Auth | `eyJhbGci...` | **BLOCKED** |
| `SUPABASE_STAGING_SERVICE_ROLE_KEY` | Supabase staging service role key | Dashboard → Settings → API | **YES — Secret Manager** | Storage, admin ops | `eyJhbGci...` | **BLOCKED** |
| `SUPABASE_STAGING_DB_PASSWORD` | Postgres connection password | Dashboard → Settings → Database | **YES — Secret Manager** | DATABASE_URL | `strong-random-password` | **BLOCKED** |
| `REDIS_HOST` | Memorystore Redis private IP | Provisioned by Terraform | No | REDIS_URL construction | `10.10.0.5` | **BLOCKED** — Terraform not yet applied |
| `FERNET_KEY` | Symmetric encryption key for stored provider keys | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | **YES — Secret Manager** | Backend crypto | `Fm5K...=` | **BLOCKED** |
| `GROQ_API_KEY` | Groq cloud LLM API key | [console.groq.com](https://console.groq.com) → API Keys | **YES — Secret Manager** | AI provider | `gsk_...` | **BLOCKED** |
| `OPENAI_API_KEY` | OpenAI GPT-4o API key | [platform.openai.com](https://platform.openai.com) → API Keys | **YES — Secret Manager** | AI provider | `sk-...` | **BLOCKED** |
| `REAL_DOMAIN` | Production/staging domain (e.g. staging.praxis.yourdomain.com) | Domain registrar | No | TLS cert, CORS | `staging.praxis.yourdomain.com` | **BLOCKED** — not configured |
| `ALERT_NOTIFICATION_CHANNEL` | Cloud Monitoring notification channel | GCP Console → Monitoring → Alerting → Notification channels | No | Alerting | `projects/xxx/notificationChannels/yyy` | Optional |
| `GITHUB_REPO` | GitHub repository for WIF trust | Auto-detected: `AMIYA8597/praxis-interviewOS` | No | Workload Identity | `owner/repo` | **PASS** — detected |

---

## Step-by-Step Bootstrap Commands

Run these in order. Each step is blocked on the prerequisite above it.

### Step 1 — Create GCP staging project

```bash
# Check available billing accounts
gcloud billing accounts list

# Create project
gcloud projects create praxis-staging --name="PRAXIS Staging"

# Link billing
gcloud billing projects link praxis-staging --billing-account=BILLING_ACCOUNT_ID
```

### Step 2 — Bootstrap Terraform state bucket

```bash
cd infra/bootstrap
terraform init
terraform apply \
  -var="project_id=praxis-staging" \
  -var="environment=staging"
# Copy the output bucket name into infra/gcp/environments/staging/backend.conf
```

### Step 3 — Create Supabase staging project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. New project → choose a region close to `us-central1` (e.g. `us-east-1`)
3. Note the project URL, anon key, service_role key, and DB password
4. Install Supabase CLI: `winget install Supabase.CLI`

### Step 4 — Link Supabase and run migrations

```bash
supabase login
supabase link --project-ref STAGING_PROJECT_REF
supabase db push
```

### Step 5 — Create Secret Manager secrets

```bash
# For each secret below, never pipe real values through shell history:
echo -n "VALUE" | gcloud secrets create praxis-database-url \
  --data-file=- --project=praxis-staging

# Required secrets:
#   praxis-database-url          → postgresql+asyncpg://...
#   praxis-redis-url             → redis://REDIS_HOST:6379/0  (after Terraform apply)
#   praxis-supabase-url          → https://xxx.supabase.co
#   praxis-supabase-anon-key     → eyJ...
#   praxis-supabase-service-role-key  → eyJ...
#   praxis-fernet-key            → Fernet.generate_key()
#   praxis-groq-api-key          → gsk_...
#   praxis-openai-api-key        → sk-...
```

### Step 6 — Run Terraform

```bash
cd infra/gcp/environments/staging
terraform init -backend-config=backend.conf
terraform plan -var-file=terraform.tfvars -var="image_tag=PLACEHOLDER_DO_NOT_APPLY"
# Review plan carefully — no destructive operations should appear on first apply.
# After first CI build pushes images, re-apply with real image_tag.
```

### Step 7 — Build and push images via Cloud Build

Triggered automatically on `git push origin main` once the Cloud Build trigger is configured.

```bash
# Manual trigger for testing:
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --substitutions="_STAGING_PROJECT=praxis-staging,_REGISTRY_PROJECT=praxis-staging,_REGION=us-central1" \
  --project=praxis-staging
```

---

## Secret Manager secrets manifest

These secrets must exist in the staging project before Cloud Run services can start:

| Secret Name | Description | Used By |
|---|---|---|
| `praxis-database-url` | PostgreSQL connection string | API, Realtime, Worker |
| `praxis-redis-url` | Redis connection string | API, Realtime, Worker |
| `praxis-supabase-url` | Supabase project URL | API, Realtime |
| `praxis-supabase-anon-key` | Supabase anon key | API |
| `praxis-fernet-key` | Fernet encryption key | API, Worker |
| `praxis-groq-api-key` | Groq API key | Worker |
| `praxis-openai-api-key` | OpenAI API key | Worker |

---

*Last updated: 2026-10-05*
