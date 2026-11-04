# PRAXIS InterviewOS — Deployment Gap Analysis & Readiness Ledger

**Audit Date:** 2026-11-04  
**Target Environment:** Google Cloud Platform (GCP) — Region: `asia-south1` (or configured region)  
**Deployment Model:** Containerized microservices on Cloud Run, Cloud SQL PostgreSQL 17+, Memorystore Redis 7, Cloud Storage, Secret Manager.

---

## 1. Readiness vs. Blocker Summary

| Layer / Component | Target Production Solution | Current State in Repository | Blocker / Action Required | Status |
|---|---|---|---|---|
| **API Service** | Google Cloud Run (`praxis-api`) | Dockerfile and application code complete and tested (222/223 passed) | None in application code; container build verified in CI | **READY_FOR_DEPLOYMENT** |
| **Realtime Service** | Google Cloud Run (`praxis-realtime`, session affinity, WebSockets) | Dockerfile, binary framing protocol, Redis state machine complete (35/35 passed) | None in application code; WebSocket protocol verified | **READY_FOR_DEPLOYMENT** |
| **Worker Service** | Google Cloud Run (`praxis-worker`, ARQ queue consumer) | Dockerfile and ARQ job implementations complete (idempotency, deletion) | Worker pool concurrency scaling via Cloud Run service or job | **READY_FOR_DEPLOYMENT** |
| **Sandbox Service** | Hardened isolated container (`praxis-sandbox`) | Dockerfile, resource limits, no-egress verified (7/7 tests passed) | Runs as private internal microservice without ingress | **READY_FOR_DEPLOYMENT** |
| **Database** | Cloud SQL for PostgreSQL 17+ with `pgvector` | 31 Supabase migrations complete, 70/70 business tables enforce `FORCE RLS` | Cloud SQL instance provisioned via Terraform | **READY_FOR_DEPLOYMENT** |
| **Cache & Queue** | Memorystore for Redis 7 | Transient state and rate limiter Redis client configured | Memorystore Redis instance provisioned via Terraform | **READY_FOR_DEPLOYMENT** |
| **Object Storage** | Google Cloud Storage (Private buckets) | GCS client adapter implemented with signed URLs (`backend/app/core/storage.py`) | Storage bucket created via Terraform | **READY_FOR_DEPLOYMENT** |
| **Secret Management** | Google Secret Manager | Pinned secret versions configured in Terraform (`infra/gcp/main.tf`) | Secrets populated in Secret Manager before Cloud Run launch | **PREREQUISITE_CONFIG** |
| **AI Cloud Inference** | Free-tier Groq (`llama-3.3-70b`) or Gemini (`gemini-2.5-flash`) | Gateway router, budget guard, and fallback chains verified | Fresh free-tier API key required for zero-spend verification; paid OpenAI/Anthropic/DeepSeek active | **BLOCKED_ON_CREDENTIALS** |
| **Cloud Provisioning** | Terraform (`infra/gcp/`) | Complete Terraform scripts with least-privilege IAM, Direct VPC | Live GCP apply held awaiting authorized project credentials | **BLOCKED_ON_AUTHORIZATION** |

---

## 2. Infrastructure Deployment Prerequisite Matrix

In strict compliance with non-negotiable engineering rule #14 ("Never deploy production infrastructure, incur material cloud costs, destroy resources or rotate credentials without explicit authorization"):

1. **GCP Project Authorization:**
   - Command: `gcloud auth application-default login` or GitHub OIDC Workload Identity Federation.
   - Target project ID and region must be set in `infra/gcp/environments/staging/terraform.tfvars`.

2. **Google Secret Manager Provisioning:**
   - The following secrets must be registered in Secret Manager before Cloud Run instances start:
     - `database-url`: Connection string to Cloud SQL / Supabase PostgreSQL.
     - `jwt-secret`: 256-bit secret for JWT signing and verification.
     - `redis-url`: Memorystore Redis connection string.
     - `ai-provider-keys`: JSON bundle or individual keys for OpenAI, Anthropic, Groq, or Gemini.

3. **Artifact Registry Repository:**
   - Docker images tagged by immutable git SHA (`${SHORT_SHA}`) built via Cloud Build:
     - `${_REGION}-docker.pkg.dev/${_PROJECT_ID}/praxis/api:${SHORT_SHA}`
     - `${_REGION}-docker.pkg.dev/${_PROJECT_ID}/praxis/realtime:${SHORT_SHA}`
     - `${_REGION}-docker.pkg.dev/${_PROJECT_ID}/praxis/worker:${SHORT_SHA}`
     - `${_REGION}-docker.pkg.dev/${_PROJECT_ID}/praxis/sandbox:${SHORT_SHA}`
   - Prohibits `:latest` tag in production releases.

4. **Zero-Spend Verification Unblocking:**
   - Add a valid free-tier API key to `.env`:
     ```bash
     GROQ_API_KEY=gsk_...
     # or
     GEMINI_API_KEY=AIzaSy...
     ```
   - Verify live cloud inference acceptance:
     ```powershell
     python scripts/verify_live_inference.py
     pytest tests/integration/test_live_inference_acceptance.py -v
     ```
