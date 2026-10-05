# PRAXIS — Deployment State Audit
**Date:** 2026-10-05  
**Commit:** ed5ea37 (main, post-merge of stage7-phases51-84)  
**Branch:** main  
**Git status:** Clean (no uncommitted changes)  
**Open PRs:** None

---

## Summary

| Area | Status |
|------|--------|
| CI (GitHub Actions) | ✅ IMPLEMENTED — green (backend-tests, frontend-checks, secrets-scan) |
| Migrations | ✅ IMPLEMENTED — 20 SQL files, fully ordered |
| Dockerfiles | ✅ IMPLEMENTED — api, realtime, worker (multi-stage, non-root) |
| Terraform / IaC | ✅ IMPLEMENTED — all GCP resources defined; NOT yet applied |
| Cloud Build | ✅ IMPLEMENTED — build + push + staging deploy pipeline defined; NOT connected to real project |
| Vercel config | ✅ IMPLEMENTED — vercel.json with CSP headers, env references; NOT deployed |
| GCP projects | ❌ MISSING — `praxis-staging` and `praxis-production` GCP projects do not exist |
| Artifact Registry | ❌ MISSING — no registry created yet |
| Cloud Run services | ❌ MISSING — not provisioned |
| Memorystore Redis | ❌ MISSING — not provisioned |
| Secret Manager | ❌ MISSING — secrets not loaded |
| GCP Workload Identity | ❌ MISSING — not configured (GitHub Actions → GCP OIDC) |
| Supabase staging | ❌ MISSING — no dedicated staging project |
| Vercel deployment | ❌ MISSING — not deployed to Vercel |
| Docker images built | ❌ UNVERIFIED — never built in this environment |
| Staging E2E | ❌ MISSING — no real staging infra to test against |

---

## Detailed Status

### ✅ IMPLEMENTED

#### CI (`.github/workflows/ci.yml`)
- backend-tests: migrations + RLS + pytest (all pass on main)
- frontend-checks: pnpm typecheck + lint + next build
- secrets-scan: trufflesecurity/trufflehog
- All three checks green on commit `ed5ea37`

#### Database Migrations (`supabase/migrations/`)
20 migration files — fully ordered, including:
- Core schema, vector indexes, RLS policies, storage buckets
- Candidate memory, adaptive difficulty, interviewer personality
- Session analytics, provider observability, worker idempotency
- Storage security (no-op in CI; applies via supabase db push)

#### Dockerfiles (`docker/`)
- `Dockerfile.api` — multi-stage, python:3.11.11-slim, non-root `praxis` user, port 8000
- `Dockerfile.realtime` — includes ffmpeg, onnxruntime for VAD/STT
- `Dockerfile.worker` — ARQ worker, includes tesseract for resume parsing
- All use `requirements-lock.txt` for deterministic deps
- Never built against real registry yet

#### Terraform (`infra/gcp/`)
All GCP resources defined in `main.tf`:
- VPC, subnet, VPC connector
- Memorystore Redis
- Service accounts (api, realtime, worker, deployer) with least-privilege IAM
- Workload Identity Pool for GitHub Actions OIDC
- Artifact Registry
- Cloud Run v2 (api, realtime)
- Global HTTPS load balancer with managed SSL
- Cloud Armor security policy
- Separate tfvars for staging and production

**NOT APPLIED** — `terraform init` / `apply` never run.  
Staging project ID: `praxis-staging` (placeholder — GCP project not created).  
Production project ID: `praxis-production` (placeholder — GCP project not created).  
Domain: `praxis.example.com` (placeholder — real domain not set).

#### Cloud Build (`cloudbuild.yaml`)
- Builds all 3 images, pushes to Artifact Registry
- Deploys to staging Cloud Run
- Runs staging smoke test (health check)
- Tags as `latest` after smoke test passes
- **NOT connected** — no GCP project, no trigger configured

#### Vercel (`vercel.json`)
- Framework: Next.js, build via `pnpm --filter web run build`
- Security headers: X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy
- Rewrites: `/api/*` → `https://api.praxis.example.com`, `/realtime/*` → `https://realtime.praxis.example.com`
- Env vars reference Vercel secrets (e.g. `@praxis-supabase-url`)
- **NOT deployed** — Vercel project not created, secrets not set

#### Scripts
| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/migrate.py` | Apply migrations via asyncpg | IMPLEMENTED |
| `scripts/final_quality_gate.py` | 15-check quality gate | IMPLEMENTED |
| `scripts/check_production_readiness.py` | 8-check readiness | IMPLEMENTED |
| `scripts/check_disaster_recovery.py` | DR verification | IMPLEMENTED |
| `scripts/check_no_fake_data.py` | No-fake-data gate | IMPLEMENTED |
| `scripts/smoke-test-queue.py` | Worker smoke | IMPLEMENTED |

#### Documentation (`docs/`)
- `ARCHITECTURE_PRODUCTION.md` — GCP target architecture described
- `DEPLOYMENT.md` — deployment runbook
- `PRODUCTION_RUNBOOK.md` — operational procedures
- `PRODUCTION_CERTIFICATION.md` — certification checklist (not yet signed off)
- `RELEASE_PROCESS.md` — release procedure
- `BACKUP_STRATEGY.md` — RPO/RTO targets documented

---

### ❌ MISSING

| Item | Blocker |
|------|---------|
| GCP project `praxis-staging` | Must be created manually in GCP Console |
| GCP project `praxis-production` | Must be created manually |
| Billing accounts linked | Required before any GCP resource |
| `praxis-staging` APIs enabled | Terraform does this after project exists |
| Artifact Registry | Created by Terraform after project exists |
| GCP Workload Identity for GitHub | Created by Terraform |
| Supabase staging project | Must be created at supabase.com |
| Real domain | `praxis.example.com` is a placeholder |
| Vercel project + secrets | Must be created at vercel.com |
| Docker images pushed to registry | No registry exists yet |
| Cloud Run deployments | No project to deploy to |

---

### ⚠️ PARTIAL

| Item | What exists | What's missing |
|------|------------|----------------|
| `infra/gcp/main.tf` | All resources defined | `backend "gcs"` bucket for Terraform state not created |
| `cloudbuild.yaml` | Full pipeline defined | Not triggered; `STAGING_API_URL` is placeholder |
| `vercel.json` | Config complete | Vercel project not created; env vars not set |
| `infra/gcp/environments/staging/terraform.tfvars` | File exists | `domain` = placeholder, `image_tag` = "latest" |
| `infra/gcp/environments/production/terraform.tfvars` | File exists | `domain` = placeholder, `image_tag` = "REPLACE_WITH_IMMUTABLE_TAG" |
| `requirements-lock.txt` | 54 lines | Does not match `backend/requirements.txt` exactly (stale lock) |

---

### 🔴 BROKEN

| Item | Issue |
|------|-------|
| `infra/gcp/environments/staging/terraform.tfvars` | `image_tag = "latest"` — violates immutable-tag policy |
| `vercel.json` rewrites | Target URLs use `praxis.example.com` — will 404 in all deployments |
| CSP in `vercel.json` | `connect-src` includes `wss://*.praxis.example.com` — placeholder domain |
| `cloudbuild.yaml` smoke test | Hits `https://api.staging.praxis.example.com` — does not exist |

---

### ❓ UNVERIFIED

| Item | Why unverified |
|------|---------------|
| Docker image builds | Never built in this environment |
| `requirements-lock.txt` consistency | Generated at phase time; may not match current `backend/requirements.txt` |
| Terraform plan output | Never run against a real GCP project |
| RLS tests against real Supabase | Only run against local pgvector in CI |
| Electron production build | Not attempted |
| Audio protocol (PCM16, VAD, STT) | Tested only in unit tests |
| Dual-path coaching timing | Unit tested; not measured on real infra |

---

## Local Toolchain

| Tool | Available | Version |
|------|-----------|---------|
| Python | ✅ | 3.13.7 |
| pip | ✅ | 26.2.1 |
| Node.js | ✅ | v24.18.0 |
| pnpm | ✅ | 10.30.3 |
| Docker | ✅ | 29.7.2 |
| gcloud CLI | ✅ | project = tradebit-396406 (wrong project) |
| Terraform | ❌ | not installed |
| Vercel CLI | ❌ | not installed |
| Supabase CLI | ❌ | not installed |

---

## What Must Happen Before Any Deployment

### Immediate prerequisites (manual, one-time)
1. Create GCP project `praxis-staging` (or choose an existing project)
2. Link billing to that project
3. Create a real domain OR pick a subdomain of an existing one
4. Create Supabase staging project at supabase.com
5. Create Vercel project linked to `AMIYA8597/praxis-interviewOS`
6. Install: `terraform`, `vercel`, `supabase` CLI tools
7. Configure `gcloud` to point at the staging project

### Then (automatable)
8. Create GCS bucket for Terraform state
9. `terraform init && terraform apply` for staging
10. Load secrets into Secret Manager
11. Build and push Docker images to Artifact Registry
12. Deploy Cloud Run services
13. Apply Supabase migrations to staging
14. Deploy Next.js to Vercel (preview/staging)
15. Run smoke tests

---

## Conclusion

The **code and IaC are production-ready in structure**. All the Terraform, Dockerfiles, Cloud Build pipeline, Vercel config, migrations, and service code exist and are implemented.

**Nothing is deployed.** No GCP staging project exists. No Supabase staging project exists. No Vercel project exists. No images have been pushed.

The next action is to **provision the real GCP project and Supabase project**, then apply Terraform, then build/push images, then deploy.
