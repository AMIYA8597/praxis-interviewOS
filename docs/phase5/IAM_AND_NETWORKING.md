# PRAXIS InterviewOS — IAM Roles & Cloud Networking Architecture

**Document ID**: PROD-IAM-NET-001  
**Milestone**: Phase 5 — Production Engineering  
**Security Standard**: Least-Privilege IAM, Dedicated Service Accounts, Private VPC Access  
**Date**: 2026-11-01  
**Status**: Authoritative IAM and Networking Specification  

---

## 1. Identity & Access Management (IAM)

PRAXIS strictly prohibits using broad `Owner` or `Editor` roles. Every microservice runs under a dedicated Google Service Account with narrowly scoped permissions.

### 1.1 Service Account Matrix
| Service Account | Bound Cloud Run Service | Assigned IAM Roles | Purpose |
| :--- | :--- | :--- | :--- |
| `sa-praxis-api` | `praxis-api` | `roles/secretmanager.secretAccessor`<br>`roles/monitoring.metricWriter`<br>`roles/logging.logWriter`<br>`roles/vpcaccess.user` | Read database credentials, write telemetry, access private Redis |
| `sa-praxis-realtime` | `praxis-realtime` | `roles/secretmanager.secretAccessor`<br>`roles/monitoring.metricWriter`<br>`roles/logging.logWriter`<br>`roles/vpcaccess.user` | Read AI/JWT keys, write telemetry, access private Redis |
| `sa-praxis-worker` | `praxis-worker` | `roles/secretmanager.secretAccessor`<br>`roles/monitoring.metricWriter`<br>`roles/logging.logWriter`<br>`roles/storage.objectAdmin`<br>`roles/vpcaccess.user` | Dequeue ARQ tasks, process resume files in S3/GCS |
| `sa-cloudbuild` | Cloud Build CI/CD | `roles/run.admin`<br>`roles/artifactregistry.writer`<br>`roles/iam.serviceAccountUser` | Build images, push to registry, deploy Cloud Run services |

### 1.2 Key Security Invariants
- **Zero Service Account JSON Keys in Source**: Workload Identity Federation or Cloud Build native service accounts are used exclusively. No service account JSON key files are stored in git or environment variables.
- **Resource-Level Secret Scoping**: `sa-praxis-api` is granted access only to the specific secrets it requires (`DATABASE_URL`, `SUPABASE_JWT_SECRET`), preventing lateral secret discovery.

---

## 2. Cloud Networking & Egress Architecture

```mermaid
flowchart TD
    subgraph Public Internet
        Client[Web & Desktop Clients]
        SupabaseDB[Supabase Postgres\neu-central-1 (SSL Require)]
        ExternalLLM[OpenRouter / Gemini / DeepSeek\nHTTPS 443]
    end

    subgraph GCP asia-south1
        LB[Cloud Run Ingress / HTTPS]

        subgraph Serverless Compute
            API[praxis-api]
            RT[praxis-realtime]
            Worker[praxis-worker]
        end

        subgraph VPC Network: praxis-vpc
            VPCConnector[Serverless VPC Connector\n10.8.0.0/28]
            Redis[(Memorystore Redis 7\n10.0.0.4:6379\nPrivate IP Only)]
        end
    end

    Client -->|HTTPS / WSS| LB --> API
    LB --> RT

    API -->|VPC Egress (Private Ranges)| VPCConnector --> Redis
    RT -->|VPC Egress (Private Ranges)| VPCConnector --> Redis
    Worker -->|VPC Egress (Private Ranges)| VPCConnector --> Redis

    API -->|Direct Egress (Public Ranges)| SupabaseDB
    Worker -->|Direct Egress (Public Ranges)| SupabaseDB
    API -->|Direct Egress (Public Ranges)| ExternalLLM
    RT -->|Direct Egress (Public Ranges)| ExternalLLM
```

### 2.1 Serverless VPC Access Connector
- **Connector Name**: `praxis-vpc-connector`
- **Subnet CIDR**: `10.8.0.0/28` (Non-overlapping with Redis VPC range `10.0.0.0/16`)
- **Egress Policy**: `all-traffic` or `private-ranges-only` (Routed through VPC connector for RFC 1918 addresses, while direct public egress reaches external AI APIs and Supabase via TLS).

### 2.2 Redis Isolation
- Memorystore Redis is bound strictly to private IP `10.0.0.4:6379`.
- Public internet access to Redis is **completely disabled** at the VPC network layer.
- Redis requires password authentication (`AUTH`) and optional in-transit encryption (`TLS`).
