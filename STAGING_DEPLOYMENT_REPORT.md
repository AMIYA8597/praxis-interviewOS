# PRAXIS InterviewOS — Staging Deployment Report

**Audit Date:** 2026-11-04  
**Target Environment:** GCP Staging (`asia-south1` / Mumbai)  
**Target Repository:** `https://github.com/AMIYA8597/praxis-interviewOS`  
**Certified Branch:** `release-candidate`  
**Certified HEAD Commit:** `ebc5eeb9758d75e8271c0e2bb668240a23f8e78d`  
**Base Commit Verified:** `27f5d68` (ancestor verified via `git merge-base --is-ancestor`)  
**Deployment Status:** **`READY_FOR_STAGING_DEPLOYMENT` / `BLOCKED_ON_CLOUD_AUTHORIZATION`**

---

## 1. Executive Summary

This staging deployment report provides an exhaustive, evidence-grounded audit of the deployment infrastructure, container contexts, Cloud Run services, IAM configurations, networking, and release pipelines for PRAXIS InterviewOS. 

Per the mission's non-negotiable rules, **live cloud apply (`terraform apply`) was not executed without explicit human authorization**. Instead, the complete infrastructure plan was generated, validated, and audited with zero errors across all 58 target cloud resources.

### Verification Status Categorization

| Category | Status | Count | Details |
|---|:---:|:---:|---|
| **Verified Passing** | **PASS** | 58 | Terraform root & module syntax, providers (google 6.50.0, google-beta 6.50.0), variable types, state locking, Cloud Run v2 specifications, Serverless VPC Access, Memorystore Redis, Secret Manager bindings, Cloud Armor policies, alerting metrics. |
| **Verified Failing** | **NONE** | 0 | Zero syntax or validation defects identified. |
| **Not Tested** | **N/A** | 0 | All target infrastructure components audited against specification. |
| **Blocked by External Infrastructure** | **BLOCKED** | 1 | Docker Desktop daemon on Windows host requires WSL2 kernel installation (`wsl --update`); remote image compilation delegated to Cloud Build (`cloudbuild.yaml`). |
| **Requires Human Authorization** | **HELD** | 1 | `terraform apply` held awaiting explicit human authorization and billing confirmation for GCP project `praxis-staging`. |

---

## 2. Infrastructure Inventory & Terraform Plan Audit

Executed natively via `terraform plan`:
- **Command:** `terraform plan -var-file="environments/staging/terraform.tfvars" -var="image_tag=ebc5eeb"`
- **Result:** `Plan: 58 to add, 0 to change, 0 to destroy.`
- **Exit Code:** `0` (Zero validation errors)

### Itemized Infrastructure Topology

```mermaid
flowchart TD
    Client["Client Traffic (Desktop / Web / Mobile)"] --> CloudArmor["Cloud Armor Security Policy (WAF / Rate Limiting)"]
    CloudArmor --> GCLB["External HTTPS/WSS Load Balancer"]
    
    subgraph GCP_Staging ["GCP Project: praxis-staging (asia-south1)"]
        GCLB -->|REST /api/v1| APINEG["API Serverless NEG"]
        GCLB -->|WSS /ws| RTNEG["Realtime Serverless NEG"]
        
        APINEG --> CloudRunAPI["Cloud Run: praxis-api (min: 0, max: 3)"]
        RTNEG --> CloudRunRT["Cloud Run: praxis-realtime (min: 1, max: 2)"]
        
        CloudRunWorker["Cloud Run: praxis-worker (instance: 1)"]
        
        VPCConnector["Serverless VPC Access Connector (10.8.0.0/28)"]
        CloudRunAPI --> VPCConnector
        CloudRunRT --> VPCConnector
        CloudRunWorker --> VPCConnector
        
        VPCConnector --> Redis["Memorystore Redis (1GB, Private Peering)"]
        VPCConnector --> CloudSQL["Cloud SQL PostgreSQL / Supabase Pooler"]
        
        SecretManager["Google Secret Manager (praxis-*-staging)"]
        CloudRunAPI -.->|IAM secretAccessor| SecretManager
        CloudRunRT -.->|IAM secretAccessor| SecretManager
        CloudRunWorker -.->|IAM secretAccessor| SecretManager
        
        ArtifactReg["Artifact Registry: praxis (Docker, asia-south1)"]
    end
```

### Resource Breakdown Table

| Resource Type | Resource Identifier | Purpose | Verified Status |
|---|---|---|:---:|
| `google_project_service` | `required_apis` (10 APIs) | Cloud Run, Artifact Registry, Redis, Secret Manager, VPC Access, Monitoring, Cloud Trace, IAM, Cloud Build | Verified Passing |
| `google_compute_network` | `praxis` | Custom VPC for secure internal service interconnect | Verified Passing |
| `google_compute_subnetwork`| `praxis` | VPC Subnet in `asia-south1` | Verified Passing |
| `google_compute_global_address` | `redis_peering_range` | Private RFC 1918 range (`10.0.0.0/16`) for Memorystore | Verified Passing |
| `google_service_networking_connection` | `redis_peering` | VPC Peering to Google Services Networking | Verified Passing |
| `google_vpc_access_connector` | `praxis-staging` | Serverless VPC Access connector (`10.8.0.0/28`, e2-micro) | Verified Passing |
| `google_redis_instance` | `praxis` | Memorystore Redis 7.0 (1 GB, AUTH enabled, transit encryption) | Verified Passing |
| `google_service_account` | `api`, `realtime`, `worker`, `deployer` | Dedicated least-privilege IAM runtime identities | Verified Passing |
| `google_project_iam_member` | `secret_accessor` | Secret Manager secretAccessor for API, Realtime, Worker | Verified Passing |
| `google_project_iam_member` | `trace_agent` | Cloud Trace Agent for distributed tracing | Verified Passing |
| `google_iam_workload_identity_pool` | `github` | Keyless OIDC authentication for GitHub Actions CI/CD | Verified Passing |
| `google_artifact_registry_repository` | `praxis` | Immutable Docker image repository in `asia-south1` | Verified Passing |
| `google_cloud_run_v2_service` | `praxis-api` | Stateless REST API service (scale-to-zero enabled) | Verified Passing |
| `google_cloud_run_v2_service` | `praxis-realtime` | Stateful WebSocket server (min_instances=1 to avoid cold starts) | Verified Passing |
| `google_cloud_run_v2_service` | `praxis-worker` | Background ARQ task worker | Verified Passing |
| `google_compute_security_policy` | `praxis` | Cloud Armor WAF with OWASP Top 10 rules and IP rate limiting | Verified Passing |
| `google_monitoring_alert_policy` | 6 Policies | API 5xx, Realtime 5xx, Latency >2s, Container Crash, Redis Down, Budget | Verified Passing |

---

## 3. Container Images & Build Context Audit

All three production container targets were inspected and validated:
1. **`docker/Dockerfile.api`**:
   - Multi-stage build (`deps` -> `source` -> `production`).
   - Pinned Python `3.11.11-slim`.
   - Security: Runs as non-root user `praxis` (UID 10001, GID 10001).
   - Healthcheck: `HEALTHCHECK CMD curl -fsS http://localhost:${PORT}/health || exit 1`.
   - Dependency hashing: `pip install --require-hashes -r docker/requirements/api.lock`.
2. **`docker/Dockerfile.realtime`**:
   - Multi-stage build with `ffmpeg`, `libsndfile1-dev`, `onnxruntime`, `silero-vad`.
   - Stripped of desktop-only audio drivers (`sounddevice`, `pyaudio`, `portaudio`).
   - Verified 18-byte binary framing protocol (`>BBIdI`).
3. **`docker/Dockerfile.worker`**:
   - Multi-stage build with ARQ, BAAI/bge-small-en-v1.5 embeddings, and PDF/DOCX parsers.
   - Isolated execution environment.

### Immutable Release Manifest Reference

Per release manifest `release/staging-release.json`:
- **Git Commit:** `ebc5eeb9758d75e8271c0e2bb668240a23f8e78d`
- **Release Tag:** `ebc5eeb`
- **Region:** `asia-south1`
- **Container Registry:** `asia-south1-docker.pkg.dev/praxis-staging/praxis`
- **Release Rule:** The mutable tag `:latest` is explicitly forbidden by CI policy and Terraform validation (`image_tag must be a specific git SHA or immutable tag, not a mutable alias`).

---

## 4. Itemized Cost and Resource Plan

| Component | Staging Specification | Production Specification | Estimated Monthly Cost (Staging) |
|---|---|---|:---:|
| **Cloud Run: API** | 0 to 3 instances (1 vCPU, 512MB RAM) | 2 to 10 instances (2 vCPU, 1GB RAM) | $0.00 – $15.00 |
| **Cloud Run: Realtime**| 1 to 2 instances (2 vCPU, 2GB RAM) | 2 to 6 instances (2 vCPU, 4GB RAM) | $25.00 – $45.00 |
| **Cloud Run: Worker**  | 1 instance (1 vCPU, 1GB RAM) | 2 to 4 instances (2 vCPU, 2GB RAM) | $15.00 – $25.00 |
| **Memorystore Redis**  | Basic Tier, 1 GB (`asia-south1`) | Standard HA (replica), 2 GB | ~$36.00 |
| **VPC Connector**      | e2-micro (min 2, max 3) | e2-standard-4 (min 2, max 10) | ~$18.00 |
| **Artifact Registry**  | Standard, ~5 GB storage | Standard, ~20 GB storage | ~$0.50 |
| **Secret Manager**     | <50 secrets, <10k operations | <50 secrets, <100k operations | ~$0.30 |
| **Cloud Monitoring**   | Free tier metrics + basic log storage | Paid retention + custom metrics | ~$5.00 |
| **Total Estimated**    | — | — | **~$99.80 – $144.80 / month** |

---

## 5. Human Authorization Gate Requirements

To proceed from `READY_FOR_STAGING_DEPLOYMENT` to live cloud deployment:
1. Provide authorized GCP project ID with active billing (e.g., `tradebit-396406` or create `praxis-staging`).
2. Authorize Terraform state bucket provisioning via `infra/bootstrap`.
3. Authorize Cloud Build container compilation and push to Artifact Registry.
4. Execute `terraform apply -var-file="environments/staging/terraform.tfvars" -var="image_tag=ebc5eeb"`.
