# PRAXIS InterviewOS — Operational Cost Model & Financial Engineering

**Document ID**: PROD-COST-001  
**Milestone**: Phase 5 — Cost Engineering & Financial Governance  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Cloud Infrastructure Cost Model & Financial Architecture  

---

## 1. Itemized Monthly Operational Cost Schedule (Baseline Sizing)

Based on Google Cloud Platform (`asia-south1`) and Supabase pricing for initial production launch (1 warm API instance, 1 warm Realtime instance, 1 background worker, up to 10,000 monthly interviews):

| Service Component | Infrastructure Provider | Specification / Tier | Monthly Fixed Cost | Variable Cost Metric |
| :--- | :--- | :--- | :---: | :--- |
| **`praxis-api`** | Google Cloud Run | 2 vCPU, 2 GiB (1 warm instance) | $\$28.50$ | $\$0.00002400/\text{vCPU-sec}$ |
| **`praxis-realtime`** | Google Cloud Run | 4 vCPU, 4 GiB (1 warm instance) | $\$56.00$ | $\$0.00003200/\text{vCPU-sec}$ |
| **`praxis-worker`** | Google Cloud Run | 2 vCPU, 2 GiB (Scale-to-zero when idle) | $\$8.50$ | Active job runtime seconds |
| **Memorystore for Redis** | Google Cloud | Basic Tier, 1 GiB (`10.0.0.4:6379`) | $\$18.50$ | Flat monthly tier |
| **Serverless VPC Connector** | Google Cloud | 2 throughput instances (`10.0.0.0/28`) | $\$7.20$ | Flat monthly baseline |
| **Database & Vector Store** | Supabase Cloud | Pro Tier (8 GiB Storage, 2 vCPU compute) | $\$25.00$ | Included in tier |
| **Cloud Storage** | Supabase Storage | 50 GiB Resumes & Audio Metadata | $\$1.05$ | $\$0.021/\text{GB-month}$ |
| **Cloud Logging & Trace** | Google Cloud | Structured JSON Logs & W3C Trace | $\$3.50$ | First 50 GiB free |
| **AI Provider Ingestion** | OpenAI / Gemini / DeepSeek | Blended model usage via AI Gateway | Variable | $\$0.0185/\text{interview session}$ |
| **Total Baseline Monthly Cost** | | | **$\approx \$148.25$** | **$<\$0.02/\text{interview}$** |

---

## 2. Growth Scenario Projections

```text
Monthly Cost ($)
 2000 ┼                                                  ● Enterprise ($1,850/mo)
 1500 ┼                                                 /
 1000 ┼                                                /
  500 ┼                           ● Growth ($450/mo)  /
  150 ┼───● Baseline ($148/mo)───/────────────────────
    0 ┼──────┬──────────────────────┬──────────────────────┬──────────────
           Pilot (1-50 users)   Growth (50-500)       Enterprise (500-2,500)
```

1. **Pilot / Launch Tier (1–50 concurrent users)**:
   - Fixed baseline: $\approx \$148.25/\text{month}$.
   - Incremental variable: $<\$0.02/\text{interview session}$.
2. **Growth Tier (50–500 concurrent users)**:
   - Fixed baseline: $\approx \$450.00/\text{month}$ (higher memory Redis 2GB + 2 vCPU database).
   - Cost per interview: Reduced to $\$0.014/\text{session}$ through prompt caching and DeepSeek token routing.
3. **Enterprise Tier (500–2,500 concurrent users)**:
   - Fixed baseline: $\approx \$1,850.00/\text{month}$ (High-Availability Redis, Multi-region Cloud Run).
   - Cost per interview: $<\$0.012/\text{session}$.

---

## 3. Financial Controls & Programmatic Quotas

1. **GCP Billing Budget Alerts**:
   - Budget threshold alert configured at $\$200.00/\text{month}$ with automated Cloud Function triggers:
     - $50\%$ ($\$100$): Notification email to Finance and DevOps leads.
     - $80\%$ ($\$160$): Warning alert in `#praxis-ops` Slack channel.
     - $100\%$ ($\$200$): P2 operational escalation.
2. **AI Gateway Token Guards**:
   - Organization daily spending cap enforced at $\$50.00/\text{day}$ via atomic Redis counters (`praxis_ai_gateway/budget.py`).
   - Requests exceeding quota are automatically routed to local HuggingFace Flan-T5, ensuring zero unexpected cloud overage bills.
