# PRAXIS InterviewOS — Google Cloud Infrastructure Specification

**Document ID**: PROD-GCP-001  
**Milestone**: Phase 5 — Production Engineering  
**Primary Region**: `asia-south1` (Mumbai)  
**Provider**: Google Cloud Platform (Terraform Google ~> 6.14)  
**Date**: 2026-11-01  
**Status**: Authoritative GCP Infrastructure Specification  

---

## 1. Cloud Architecture & Resource Inventory

The PRAXIS backend infrastructure in GCP is provisioned as code via Terraform in [`infra/gcp/`](file:///d:/work/interviewOS/infra/gcp/).

### 1.1 Managed Resource Table
| Resource Name | GCP Service | Sizing / Configuration | Environment Role |
| :--- | :--- | :--- | :--- |
| `praxis-api` | Cloud Run Gen 2 | 1 vCPU, 1 GiB RAM, max 10 instances | REST API Gateway & Webhook ingestion |
| `praxis-realtime` | Cloud Run Gen 2 | 2 vCPU, 4 GiB RAM, min 1 instance | WebSocket speech & VAD/Whisper engine |
| `praxis-worker` | Cloud Run Gen 2 | 1 vCPU, 2 GiB RAM, 1 instance (continuous) | ARQ background job & document consumer |
| `praxis-redis` | Google Cloud Memorystore | Redis 7, 1 GiB, VPC private access | Rate limiting, session locks, ARQ broker |
| `praxis-registry` | Artifact Registry | Docker format, `asia-south1` | Secure repository for immutable images |
| `praxis-secrets` | Secret Manager | Pinned secret versions (`v1`, `v2`) | Database credentials, JWT keys, AI tokens |
| `praxis-vpc-connector`| Serverless VPC Access | CIDR `10.8.0.0/28`, throughput 200–1000 Mbps | Bridges Cloud Run to Memorystore Redis |
| `praxis-monitoring` | Cloud Monitoring & Logging | Alert policies (5xx, latency, crashes) | System observability & PagerDuty alerts |

---

## 2. Environment Isolation: Staging vs. Production

To eliminate cross-contamination, Staging and Production utilize separate Terraform workspaces and configurations:

```
infra/gcp/environments/
├── staging/
│   ├── backend.conf        # GCS bucket: praxis-staging-tfstate
│   └── terraform.tfvars    # project_id = "praxis-staging", min_instances = 0
└── production/
    ├── backend.conf        # GCS bucket: praxis-production-tfstate
    └── terraform.tfvars    # project_id = "praxis-production", min_instances = 1
```

### Invariants Between Environments
1. **Zero Shared Databases**: Staging points to an isolated staging Supabase project; it CANNOT read or write to the production database.
2. **Zero Shared Storage**: Resumes uploaded in staging reside in a staging-only bucket.
3. **Separate Secret Manager Instances**: Production API keys and database credentials are fully isolated in the production GCP project.
4. **Cost Optimization in Staging**: `api_min_instances = 0` (scale to zero when idle) in staging, saving compute costs.

---

## 3. Terraform Validation Evidence

Both the bootstrap and primary infrastructure modules pass syntax and provider validation:

```bash
terraform -chdir=infra/bootstrap validate
# Success! The configuration is valid.

terraform -chdir=infra/gcp validate
# Success! The configuration is valid.
```
