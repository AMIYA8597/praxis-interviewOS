# PRAXIS InterviewOS — Google Cloud Cost & Resource Budget Plan

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Target Region:** `asia-south1` (Mumbai)  

---

## 1. Staging Monthly Expenditure Breakdown

| Infrastructure Component | Sizing & Configuration | Free-Tier Allowance | Chargeable Estimate (Staging) |
|---|---|---|---|
| **Cloud Run: `praxis-api`** | 1 vCPU, 1024 MiB, 0-3 instances (scale-to-zero) | 2M requests/mo, 360,000 GB-s | **$0.00** (within free tier) |
| **Cloud Run: `praxis-realtime`** | 1 vCPU, 2048 MiB, 1 min instance (low cold-start) | 2M requests/mo | **~$18.00 / mo** (idle 1 instance) |
| **Cloud Run: `praxis-worker`** | 1 vCPU, 2048 MiB, 1 instance (ARQ queue consumer) | 2M requests/mo | **~$18.00 / mo** |
| **Cloud Run: `praxis-sandbox`** | 0.5 vCPU, 512 MiB, 0-2 instances (internal, scale-to-zero) | Within free tier | **$0.00** |
| **Memorystore Redis 7** | Basic Tier, 1 GB (`asia-south1`) | No free tier | **~$36.00 / mo** |
| **PostgreSQL Database** | Managed Supabase Free Tier (`rqbbfegkqmsvthdgoyqk`) | 500 MB DB, 1 GB Storage | **$0.00** |
| **Artifact Registry** | Container images (pinned SHA digests, ~2 GB total) | 0.5 GB/mo free | **~$0.15 / mo** |
| **Cloud Storage** | Private bucket (`praxis-staging-resumes`), 5 GB | 5 GB/mo free tier | **$0.00** |
| **Cloud Logging & Monitoring** | 30-day retention log sink | 50 GB log ingestion free | **$0.00** |
| **Total Estimated Staging Cost** | **Strictly Capped Cloud Infrastructure** | — | **~$72.15 / month** |

---

## 2. Hard Cost Controls & Safeguards

1. **Autoscaling Guardrails:**
   - `praxis-api`: Max 3 instances.
   - `praxis-realtime`: Max 2 instances.
   - `praxis-worker`: Max 1 instance.
   - Runaway scaling is mathematically prevented by Cloud Run service limits.
2. **GCP Budget Alerts:**
   - Hard budget alert threshold at **$50.00** (50%), **$75.00** (75%), and **$100.00** (100%).
   - Sends email notification to `amiyachowdhury04@gmail.com`.
3. **AI Gateway Token & Budget Guards:**
   - Per-session token ceiling: 4,000 tokens.
   - Per-user daily budget: $1.00 maximum spend.
   - Free-tier provider priority: Groq (`llama-3.3-70b-versatile`) and Gemini (`gemini-2.5-flash`) routed first before any paid endpoints.
