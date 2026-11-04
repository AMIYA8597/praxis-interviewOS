# PRAXIS InterviewOS — Google Cloud Production Architecture Specification

**Document Version:** 1.0.0  
**Target Platform:** Google Cloud Platform (GCP)  
**Primary Region:** `asia-south1` (Direct VPC Peering & High Availability)  
**Infrastructure as Code:** Terraform (`infra/gcp/main.tf`, `infra/terraform/`)  

---

## 1. Master System Topology

```mermaid
graph TD
    CLIENTS["Independent Frontend Clients<br/>(Web / iOS / Android / Desktop)"] --> LB["Google Cloud Load Balancer (HTTPS / WSS)<br/>+ Google Cloud Armor (DDoS / WAF)"]

    subgraph VPC ["Google Cloud Direct VPC Network (10.0.0.0/16)"]
        subgraph ServerlessCompute ["Cloud Run Managed Services"]
            API["praxis-api<br/>(Cloud Run - Concurrency: 80)"]
            RT["praxis-realtime<br/>(Cloud Run - Session Affinity, WS)"]
            WRK["praxis-worker<br/>(Cloud Run - ARQ Queue Consumer)"]
            SBX["praxis-sandbox<br/>(Cloud Run - Internal Only, No Egress)"]
        end

        subgraph ManagedData ["Managed Data Tier"]
            CSQL[("Cloud SQL for PostgreSQL 17+<br/>Authoritative Store (70 Tables, FORCE RLS)")]
            REDIS[("Memorystore for Redis 7<br/>Transient State Machine & Rate Limiter")]
            GCS[("Cloud Storage (Private Buckets)<br/>Resumes, Chunks, GDPR Exports")]
        end
    end

    subgraph SecurityAndOps ["Security & Operational Services"]
        GSM["Google Secret Manager<br/>(Pinned Versions, No Hardcoded Keys)"]
        AR["Artifact Registry<br/>(Immutable SHA Image Digests)"]
        CL["Cloud Logging & Cloud Monitoring<br/>(Prometheus Scrape, P99 Alerts)"]
        CT["Cloud Trace<br/>(OpenTelemetry Distributed Tracing)"]
    end

    LB -->|HTTPS /api/v1| API
    LB -->|WSS /ws/sessions| RT
    
    API --> CSQL
    API --> REDIS
    API --> GCS
    API -. HTTP/RPC .-> SBX
    
    RT --> CSQL
    RT --> REDIS
    
    WRK --> CSQL
    WRK --> REDIS
    WRK --> GCS
    
    API -. Read Secrets .-> GSM
    RT -. Read Secrets .-> GSM
    WRK -. Read Secrets .-> GSM
    
    ServerlessCompute -. Pull Digests .-> AR
    ServerlessCompute -. Structured Logs .-> CL
    ServerlessCompute -. Spans .-> CT
```

---

## 2. Microservice Container & Resource Matrix

| Service | Container Image Reference | CPU | Memory | Min / Max Instances | Ingress | Request Timeout | Health Probes |
|---|---|---|---|---|---|---|---|
| **`praxis-api`** | `${REGISTRY}/api:${SHORT_SHA}` | 2 vCPU | 2 GiB | 1 / 20 | All (via Cloud LB) | 60s | Startup: `/health/startup`<br/>Live: `/health/live`<br/>Ready: `/health/ready` |
| **`praxis-realtime`** | `${REGISTRY}/realtime:${SHORT_SHA}` | 2 vCPU | 4 GiB | 1 / 10 | All (Session Affinity) | 3600s (WS) | Startup: `/health/live`<br/>Live: `/health/live`<br/>Ready: `/health/ready` |
| **`praxis-worker`** | `${REGISTRY}/worker:${SHORT_SHA}` | 2 vCPU | 4 GiB | 1 / 5 | Internal Only | 900s | Internal health listener port 8000 |
| **`praxis-sandbox`** | `${REGISTRY}/sandbox:${SHORT_SHA}` | 1 vCPU | 512 MiB | 1 / 10 | Internal Only (No Egress) | 5s | Live: `/health/live` |

---

## 3. Secret Management & Workload Identity Federation

1. **Zero Committed Credentials:**
   - Production images contain zero `.env` files or API keys.
   - Pinned secrets are mounted into Cloud Run container environments directly from Google Secret Manager via IAM bindings:
     - `database-url` -> `DATABASE_URL`
     - `jwt-secret` -> `SUPABASE_JWT_SECRET`
     - `redis-url` -> `REDIS_URL`
     - `ai-provider-keys` -> `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`
2. **Workload Identity Federation for CI/CD:**
   - GitHub Actions connects to GCP without long-lived JSON service account keys.
   - Uses OIDC token exchange (`google-github-actions/auth`) granting ephemeral access to Cloud Build and Artifact Registry.

---

## 4. Immutable Release Policy: No `:latest` Tag

In strict accordance with Phase 14 engineering mandates:
- Every deployment artifact is pinned to its **immutable Git commit SHA (`${SHORT_SHA}`)** and cryptographic image digest (`sha256:...`).
- The `:latest` tag is prohibited in production deployments to guarantee that rollbacks point to identical container bits.
