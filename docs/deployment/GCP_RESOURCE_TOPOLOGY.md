# PRAXIS InterviewOS — Google Cloud Resource Topology

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Target Region:** `asia-south1` (Mumbai)  

---

## 1. Network & Resource Architecture

```
Internet
   │
   ├──────── HTTPS (Port 443) ────────► [Cloud Run: praxis-api] (Public Ingress)
   │                                        │
   ├──────── WSS (Port 443)  ────────► [Cloud Run: praxis-realtime] (Public Ingress, Session Affinity)
   │                                        │
   └──────── (Internal Only) ────────► [Cloud Run: praxis-worker] (No Public Ingress)
                                            │
                                            ▼
                               [Direct VPC Egress / Subnet]
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               │                            │                            │
               ▼                            ▼                            ▼
      [Memorystore Redis 7]        [Authoritative PostgreSQL]   [Cloud Storage (GCS)]
     (ARQ Queue, Rate Limits,       (70 Business Tables,          (Private Resumes,
      Ephemeral Session Cache)       FORCE RLS, pgvector)          Audio Artifacts)
```

---

## 2. Resource Specifications & Allocation

| Resource | Service Name | Machine / Sizing Spec | Scaling Boundaries | Ingress / Network |
|---|---|---|---|---|
| **API Service** | `praxis-api` | 1 vCPU, 1024 MiB RAM | Staging: 0 to 3 instances<br>Prod: 1 to 10 instances | Public HTTPS with CORS & Rate Limiting |
| **Realtime Service** | `praxis-realtime` | 1 vCPU, 2048 MiB RAM | Staging: 1 to 2 instances<br>Prod: 2 to 10 instances | Public WSS with Session Affinity & 60m Timeout |
| **Worker Service** | `praxis-worker` | 1 vCPU, 2048 MiB RAM | Staging: 1 instance (fixed)<br>Prod: 2 to 5 instances | Internal only (no public ingress) |
| **Sandbox Service** | `praxis-sandbox` | 0.5 vCPU, 512 MiB RAM | Staging: 0 to 2 instances<br>Prod: 1 to 5 instances | Internal only, `--network none` |
| **Cache & Queue** | `praxis-redis` | Memorystore Redis 7 Basic (1 GB) | Fixed capacity | Private Service Access / VPC peering |
| **Object Storage** | `praxis-resumes` | GCS Standard Bucket | Lifecycle: 90 days retention | Private IAM, Expiring Signed URLs |
| **Secret Store** | Secret Manager | Pinned secret versions | N/A | IAM restricted per service account |

---

## 3. High-Watermark Cost Controls & Safety Caps

1. **Maximum Instance Limits:** Cloud Run services strictly define `max_instances` (API: 3, Realtime: 2, Worker: 1) preventing autoscaling runaway.
2. **Scale-to-Zero for API:** Staging API scales to 0 instances when idle, incurring $0 compute when inactive.
3. **Log Retention Limits:** Cloud Logging sinks retain operational logs for 30 days in staging (preventing log storage cost bloat).
