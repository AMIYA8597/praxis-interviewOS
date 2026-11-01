# PRAXIS InterviewOS — Production Capacity Planning & Sizing Model

**Document ID**: PROD-CAPACITY-001  
**Milestone**: Phase 5 — Capacity Planning & Resource Engineering  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Infrastructure Capacity Model & Scaling Projections  

---

## 1. Capacity Tiers & Sizing Matrix

PRAXIS InterviewOS capacity is engineered across three progressive operational tiers based on concurrent active interview sessions:

| Resource Dimension | Tier 1: Pilot / Launch (1–50 Users) | Tier 2: Growth (50–500 Users) | Tier 3: Enterprise Scale (500–2,500 Users) |
| :--- | :--- | :--- | :--- |
| **Active Concurrent Sessions** | Up to 50 sessions | 50 to 500 sessions | 500 to 2,500 sessions |
| **Core API Containers** | 1–3 instances (2 vCPU, 2 GiB) | 3–10 instances (2 vCPU, 2 GiB) | 10–25 instances (Multi-region Cloud Run) |
| **Realtime Gateway Containers** | 1–2 instances (4 vCPU, 4 GiB) | 3–6 instances (4 vCPU, 4 GiB) | 8–20 instances (Dedicated GKE / Cloud Run) |
| **Background Workers** | 1 instance (2 vCPU, 2 GiB) | 2–4 instances (2 vCPU, 2 GiB) | 4–10 instances (Autoscaled queue workers) |
| **Memorystore Redis Tier** | 1 GiB Basic Tier | 2 GiB Basic Tier | 5 GiB High-Availability (Read Replicas) |
| **PostgreSQL Pool Limit** | 100 connections (Supabase Compute) | 250 connections (Supabase Pro/Team) | 1,000 connections (Supabase Enterprise / PgBouncer) |
| **Estimated Monthly Cloud Cost** | $\approx \$125.00/\text{month}$ | $\approx \$450.00/\text{month}$ | $\approx \$1,850.00/\text{month}$ |

---

## 2. Database Connection Sizing Mathematics

PostgreSQL connection pool invariants prevent database denial-of-service during Cloud Run horizontal scaling:

$$\text{Total Connections} = (N_{\text{API}} \times (\text{POOL} + \text{OVERFLOW})) + (N_{\text{Worker}} \times \text{WORKER\_CONNS}) + \text{Admin Reserve}$$

### Tier 1 Math Verification
- $N_{\text{API\_MAX}} = 10\text{ instances}$
- $\text{DB\_POOL\_SIZE} = 2$
- $\text{DB\_MAX\_OVERFLOW} = 3$
- $N_{\text{Worker}} = 4\text{ instances}$ (1 conn each)
- $\text{Admin Reserve} = 10\text{ connections}$
- **Calculated Peak Demand**:
  $$\text{Demand} = (10 \times (2 + 3)) + (4 \times 1) + 10 = 50 + 4 + 10 = \mathbf{64} \le 75 < 100$$
  Maintains a guaranteed 25-connection safety margin.

---

## 3. Redis Memory Sizing Model

Redis stores short-lived session state, sliding audio frame jitter buffers, rate limiting buckets, and ARQ queue tasks:
- Audio sliding buffer per active turn: $\approx 160\text{ KB}$ (max 500ms PCM16).
- Session metadata and turn state: $\approx 50\text{ KB}$.
- ARQ job payload: $\approx 10\text{ KB}$.
- **Memory footprint per active session**: $\approx 220\text{ KB}$.
- At 500 concurrent sessions: $500 \times 220\text{ KB} \approx 110\text{ MB} \ll 2\text{ GB}$ allocation ($< 6\%$ utilization).

---

## 4. Horizontal Autoscaling Triggers

- **Cloud Run API Scale-Out**:
  - Target CPU utilization: $65\%$
  - Target concurrent requests per instance: $60$ (out of 80 limit)
- **Realtime Gateway Scale-Out**:
  - Target CPU utilization: $70\%$
  - Target concurrent WebSocket connections: $15$ (out of 20 limit)
- **Worker Scale-Out**:
  - Trigger: Redis `LLEN arq:queue > 20` for $> 60\text{ seconds}$.
