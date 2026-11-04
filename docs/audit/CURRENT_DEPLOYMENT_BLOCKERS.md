# PRAXIS InterviewOS — Current Deployment Blockers

**Audit Date:** 2026-11-04  
**Audit Status:** Active Deployment Preparation  
**Target Environment:** Google Cloud Platform (Region: `asia-south1`)  

---

## 1. Active Deployment Blockers

In accordance with Section 0.2 of the non-negotiable engineering rules:
- *"Do not apply Terraform, create chargeable infrastructure, incur material cloud expenditure, destroy resources or rotate production credentials without explicit authorization."*
- *"Do not invent project IDs, domains, infrastructure IDs, credentials or environment values."*
- *"Do not claim an external cloud action succeeded unless the actual cloud response proves it."*

| Blocker ID | Classification | Description | Impact | Required Remediation |
|---|---|---|---|---|
| **BLOCKER-01** | `BLOCKED_ON_AUTHORIZATION` | GCP staging project `praxis-staging` does not exist under the active credentialed account `amiyachowdhury04@gmail.com`. | Live cloud resources (Cloud Run, Cloud SQL, Memorystore, Artifact Registry) cannot be provisioned via Terraform. | Explicit user confirmation / authorization to create `praxis-staging` or specify an existing GCP project with billing enabled. |
| **BLOCKER-02** | `BLOCKED_ON_CREDENTIALS` | Live AI provider key is not active in `.env` (revoked key was disabled to prevent 403 errors). | Live AI acceptance tests skip (`LIVE_INFERENCE_BLOCKED`). The AI gateway safely operates in zero-spend unconfigured mode. | Provide a valid, active API key for Groq (`gsk_...`) or Gemini (`AIzaSy...`) for live inference activation. |
| **BLOCKER-03** | `BLOCKED_ON_CONFIGURATION` | Secret Manager secret versions must be populated before Cloud Run services are deployed. | Cloud Run containers will fail startup probes if required secrets (`database-url`, `jwt-secret`, `redis-url`) are empty. | Populate secrets in Secret Manager during staging bootstrap. |

---

## 2. Independent Unblocked Execution Path

While Blockers 01-03 await external authorization and credential inputs, all independent engineering phases proceed unimpeded:
- Phase 1: Final Backend Independence and Build Boundary (Verified: Zero frontend imports).
- Phase 2: Authoritative Cloud Architecture Decision (Resolved: PostgreSQL authoritative persistence + Redis transient state).
- Phase 3: Google Cloud Cost, Resource, and IAM Planning (Drafted and verified).
- Phase 5: Database Migration & Schema Fresh Initialization (Tested and verified across 31 migrations).
- Phase 6: Production Containerization & Build Matrix (Dockerfiles verified for API, Realtime, Worker, Sandbox).
- Phase 7: Terraform Staging Plan Preparation (`infra/gcp` formatted, validated, plan prepared).
- Phase 11: REST API & OpenAPI Contract Independence (42 routes verified; zero UI dependencies).
- Phase 12: Realtime Protocol & Binary Framing Acceptance (18-byte framing verified).
- Phase 15: Security & Privacy Certification (70/70 tables FORCE RLS, zero hardcoded secrets).
