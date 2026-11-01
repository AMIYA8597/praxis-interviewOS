# PRAXIS InterviewOS — Capacity Planning & Resource Sizing

**Document ID**: PROD-CAPACITY-001  
**Milestone**: Phase 5 — Production Engineering  
**Capacity Scope**: Tier 1 (Pilot), Tier 2 (Growth), Tier 3 (Enterprise Scale)  
**Date**: 2026-11-01  
**Status**: Authoritative Capacity Planning Model  

---

## 1. Workload Sizing Models Across Traffic Tiers

Capacity planning is derived directly from empirical performance baselines:
- Each active interview session consumes: $1\times$ WebSocket connection, $8\text{ KB/s}$ audio streaming, 1 faster-whisper small inference context ($\approx 250\text{ MB}$ RAM, $\approx 0.35$ vCPU), and $\approx 2,500$ LLM tokens.
- Each resume upload generates $\approx 50$ document chunks ($\approx 150\text{ KB}$ text + $768$-dim float embeddings in pgvector).

### Capacity Requirements by Tier

| Infrastructure Component | Tier 1: Pilot<br>(10 Concurrent Rooms) | Tier 2: Growth<br>(50 Concurrent Rooms) | Tier 3: Enterprise<br>(200 Concurrent Rooms) | Sizing Basis |
| :--- | :---: | :---: | :---: | :--- |
| **`praxis-api` Instances** | 1–2 instances | 3–5 instances | 8–15 instances | 80 concurrent reqs / instance |
| **`praxis-realtime` Instances**| 1 instance | 3 instances | 10–12 instances | 20 concurrent rooms / instance |
| **`praxis-worker` Instances** | 1 instance | 2 instances | 4 instances | ARQ queue drain rate |
| **Cloud Memorystore (Redis)** | 1 GiB | 2 GiB | 5 GiB | Session state, rate limits, queues |
| **Supabase DB Pool Limit** | 20 connections | 50 connections | 80 connections | Pinned connection budget |
| **Daily AI Token Spend** | $\approx 250\text{K tokens}$ ($\approx \$0.50$) | $\approx 1.5\text{M tokens}$ ($\approx \$3.00$) | $\approx 6.0\text{M tokens}$ ($\approx \$12.00$) | Token budget guard calculations |
| **Storage Growth / Month** | $\approx 5\text{ GB}$ | $\approx 25\text{ GB}$ | $\approx 100\text{ GB}$ | Resumes, transcripts, embeddings |

---

## 2. Saturation Thresholds & Scaling Bottlenecks

1. **CPU Saturation on `praxis-realtime`**:  
   faster-whisper inference on CPU is the primary compute bottleneck. Cloud Run instances scale horizontally when instance CPU utilization exceeds **$65\%$**, adding new revisions before audio latency degrades.
2. **PostgreSQL Connection Limits**:  
   The primary database bottleneck is connection pool saturation. Because SQLAlchemy enforces `DB_POOL_SIZE = 2` and `DB_MAX_OVERFLOW = 3`, 15 API instances plus 4 workers will consume at most $75 + 20 = 95$ connections, safely within the 100-connection Supabase pooler limit.
3. **Redis Network Egress**:  
   Serverless VPC Access connector (`10.8.0.0/28`) provides $200\text{ Mbps}$ baseline throughput, easily supporting Tier 3 audio state and cache lookups ($< 15\text{ Mbps}$ aggregate).
