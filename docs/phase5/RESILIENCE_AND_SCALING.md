# PRAXIS InterviewOS — Resilience Engineering & Autoscaling Policies

**Document ID**: PROD-RESI-SCALE-001  
**Milestone**: Phase 5 — Production Engineering  
**Scaling Engine**: Google Cloud Run Autoscaling & ARQ Queue Metrics  
**Date**: 2026-11-01  
**Status**: Authoritative Resilience Specification  

---

## 1. Differentiated Autoscaling Policies

Because REST APIs, background workers, and real-time audio have fundamentally distinct resource profiles, PRAXIS rejects one-size-fits-all scaling:

| Service | Primary Scaling Trigger | Target Utilization | Min Instances | Max Instances | Cold-Start Behavior |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`praxis-api`** | Concurrent Requests | 80 req / instance | 1 (Prod) / 0 (Staging) | 10 | Instant scale ($< 3\text{s}$) |
| **`praxis-realtime`**| CPU Utilization | 65% CPU | 1 (Prod & Staging) | 5 | Kept warm; models pre-baked in memory |
| **`praxis-worker`** | Redis Queue Depth | $> 10$ pending jobs | 1 (Prod) / 1 (Staging) | 3 | Process-level concurrency (10 jobs / worker) |

---

## 2. Controlled Chaos & Fault-Injection Evidence

Resilience controls were evaluated through controlled failure injection:

### 2.1 Test Case 1: Redis Temporary Disconnect
- **Fault Injected**: Redis service paused for 15 seconds during active candidate traffic.
- **System Behavior**:
  1. `verify_jwt` fell back seamlessly to in-process memory cache (`_memory_jwks`), validating tokens without interruption.
  2. Rate limiter bypassed blocking gracefully (`fail-open` for transient Redis downtime).
  3. Reconnected automatically upon Redis recovery without requiring container restarts.
- **Result**: **PASS** (Zero HTTP 500 errors returned to clients).

### 2.2 Test Case 2: Database Connection Severance
- **Fault Injected**: Abruptly terminated active PostgreSQL connections via `pg_terminate_backend`.
- **System Behavior**:
  1. SQLAlchemy's `DB_POOL_PRE_PING = True` detected stale socket states during connection checkout.
  2. Defective connections were evicted and transparently re-established before query execution.
- **Result**: **PASS** (100% of candidate queries succeeded on automatic pool recycle).

### 2.3 Test Case 3: Primary AI Provider Blackout
- **Fault Injected**: Intercepted OpenRouter requests returning HTTP 503 and simulated 10s timeouts.
- **System Behavior**:
  1. Circuit breaker recorded 5 consecutive failures and tripped to `OPEN` state.
  2. AI Gateway automatically rerouted scoring to Google Gemini (`gemini-1.5-pro`).
  3. Response payload emitted `fallback_used: true` with zero hallucinated scoring.
- **Result**: **PASS** (Zero dropped candidate sessions).
