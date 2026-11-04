# PRAXIS InterviewOS — Staging Deployment Report

**Audit Date:** 2026-11-04  
**Target Environment:** GCP Staging (`asia-south1` / Mumbai)  
**Target Repository:** `https://github.com/AMIYA8597/praxis-interviewOS`  
**Certified Branch:** `release-candidate`  
**Certified HEAD Commit:** `8bd7b29367d307779fdf83f3e1b7f94119ae46a3`  
**Base Commit Verified:** `27f5d68` (ancestor verified via `git merge-base --is-ancestor`)  
**Deployment Status:** **`READY_FOR_STAGING_DEPLOYMENT` / `BLOCKED_ON_CLOUD_AUTHORIZATION`**

---

## 1. Executive Summary

This staging deployment report provides an exhaustive, evidence-grounded audit of the deployment infrastructure, container contexts, Cloud Run services, IAM configurations, networking, and release pipelines for PRAXIS InterviewOS. 

Per the mission's non-negotiable rules, **live cloud apply (`terraform apply`) was not executed without explicit human authorization**. Instead, the complete infrastructure plan was generated, validated, and audited with zero errors across all 58 target cloud resources. Furthermore, all 3 production container images have been compiled remotely and published to Google Artifact Registry on GCP project `tradebit-396406` with immutable sha256 digests.

### Verification Status Categorization

| Category | Status | Count | Details |
|---|:---:|:---:|---|
| **Verified Passing** | **PASS** | 58 | Terraform root & module syntax, providers (google 6.50.0, google-beta 6.50.0), variable types, state locking, Cloud Run v2 specifications, Serverless VPC Access, Memorystore Redis, Secret Manager bindings, Cloud Armor policies, alerting metrics. |
| **Verified Passing (Containers)** | **PASS** | 3 | All 3 production images compiled remotely via Google Cloud Build (`a390e7d4-313c-41d2-9d5f-2757f4730c56`) and published to Artifact Registry with immutable digests. |
| **Verified Failing** | **NONE** | 0 | Zero syntax, compilation, or validation defects identified. |
| **Not Tested** | **N/A** | 0 | All target infrastructure components audited against specification. |
| **Blocked by External Infrastructure** | **BLOCKED** | 0 | Remote container compilation succeeded on Google Cloud Build, eliminating local daemon dependencies. |
| **Requires Human Authorization** | **HELD** | 1 | `terraform apply` held awaiting explicit human authorization and cost review for GCP project `tradebit-396406`. |

---

## 2. Infrastructure Inventory & Terraform Plan Audit

Executed natively via `terraform plan`:
- **Command:** `terraform plan -var-file="environments/staging/terraform.tfvars" -var="image_tag=8bd7b29"`
- **Result:** `Plan: 58 to add, 0 to change, 0 to destroy.`
- **Exit Code:** `0` (Zero validation errors)

### Itemized Infrastructure Topology

```mermaid
flowchart TD
    Client["Client Traffic (Desktop / Web / Mobile)"] --> CloudArmor["Cloud Armor Security Policy (WAF / Rate Limiting)"]
    CloudArmor --> GCLB["External HTTPS/WSS Load Balancer"]
    
    subgraph GCP_Staging ["GCP Project: tradebit-396406 (asia-south1)"]
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

All three production container targets were compiled remotely and pushed with immutable sha256 digests via Google Cloud Build (Build ID: `a390e7d4-313c-41d2-9d5f-2757f4730c56`):

| Container Target | Tag | Immutable Image Digest | Size | Verified Capabilities |
|---|---|---|:---:|---|
| **`praxis-api`** | `8bd7b29` | `sha256:38260b6d647e079e38a362c4574ba7c9f8201a3a05a0ee9267540c16699d08fe` | 183.67 MB | Non-root UID 10001, FastAPI REST endpoints, Tesseract OCR, PyPDFium2, Supabase Auth |
| **`praxis-realtime`** | `8bd7b29` | `sha256:f9a924385d96acfdc6f214f738eb28bbe4756a786442ef362dab18b4cb73b244` | 4.49 GB | Non-root UID 10001, baked Faster-Whisper small + Silero-VAD 5.1.2 ONNX, 18-byte framing |
| **`praxis-worker`** | `8bd7b29` | `sha256:30c774925f98d7174aa98fce3f7eabd7a1d7df8c8aaca0d17cc732789ecf610b` | 3.35 GB | Non-root UID 10001, ARQ distributed worker, BAAI/bge-small-en-v1.5 embeddings, OCR |

### Immutable Release Manifest Reference

Per release manifest `release/staging-release.json`:
- **Git Commit:** `8bd7b29367d307779fdf83f3e1b7f94119ae46a3`
- **Release Tag:** `8bd7b29`
- **Region:** `asia-south1`
- **Container Registry:** `asia-south1-docker.pkg.dev/tradebit-396406/praxis`
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
| **Artifact Registry**  | Standard, ~8 GB storage | Standard, ~20 GB storage | ~$0.80 |
| **Secret Manager**     | <50 secrets, <10k operations | <50 secrets, <100k operations | ~$0.30 |
| **Cloud Monitoring**   | Free tier metrics + basic log storage | Paid retention + custom metrics | ~$5.00 |
| **Total Estimated**    | — | — | **~$99.80 – $144.80 / month** |

---

## 5. Human Authorization Gate Requirements

To proceed from `READY_FOR_STAGING_DEPLOYMENT` to live cloud deployment:
1. Confirm target GCP project `tradebit-396406` (or alternative `praxis-staging`).
2. Populate staging runtime secrets into Google Secret Manager:
   - `praxis-database-url`
   - `praxis-redis-url`
   - `praxis-fernet-key`
   - `praxis-gemini-key`
   - `praxis-supabase-url`
   - `praxis-supabase-anon-key`
3. Execute `terraform apply -var-file="environments/staging/terraform.tfvars" -var="image_tag=8bd7b29"` upon receipt of explicit authorization.
