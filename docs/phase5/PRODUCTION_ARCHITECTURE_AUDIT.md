# PRAXIS InterviewOS — Production Architecture Audit

**Document ID**: PROD-ARCH-001  
**Milestone**: Phase 5 — Production Engineering & Operations  
**Date**: 2026-11-01  
**Status**: Authoritative Architectural Audit  

---

## 1. System Topology Overview

PRAXIS InterviewOS is a distributed, multimodal technical interview and coaching system. It decouples high-throughput, stateless HTTP REST operations from low-latency, stateful WebSocket speech pipelines and asynchronous background worker queues.

```mermaid
flowchart TD
    subgraph Client Layer
        Web[Next.js 15 Web Client\n(Dashboard, Analytics, Profile)]
        Desktop[Electron Desktop Client\n(Live Practice Arena, System Audio)]
    end

    subgraph Ingress & Edge
        EdgeMW[Next.js Edge Middleware\n(CSP, HSTS, Session Check)]
        GCP_LB[GCP Cloud Load Balancer / Ingress]
    end

    subgraph Compute Layer (Google Cloud Run / asia-south1)
        API_Svc[praxis-api\nFastAPI REST Engine]
        RT_Svc[praxis-realtime\nWebSocket Audio Agent]
        Worker_Svc[praxis-worker\nARQ Background Worker]
    end

    subgraph Data & State Tier
        Supabase_PG[(Supabase PostgreSQL\npgvector, 71 Tables, RLS)]
        Redis_Store[(Redis Instance\nSession State, JWKS, Budgets, ARQ)]
        S3_Buckets[(Object Storage / Buckets\nEncrypted Resumes, Transcripts)]
    end

    subgraph AI Gateway & Models
        AIGW[PRAXIS AI Gateway\n(Router, Circuit Breakers)]
        RemoteLLM[External LLMs\nOpenRouter, DeepSeek, Gemini]
        LocalML[faster-whisper small & silero-vad\nBaked in realtime container]
    end

    Web -->|HTTPS| EdgeMW --> GCP_LB --> API_Svc
    Desktop -->|WSS Audio 16kHz PCM| GCP_LB --> RT_Svc
    Desktop -->|HTTPS REST| GCP_LB --> API_Svc

    API_Svc -->|SQLAlchemy + asyncpg| Supabase_PG
    API_Svc -->|Cache & Enqueue| Redis_Store
    API_Svc -->|Inference| AIGW

    RT_Svc -->|Local Inference| LocalML
    RT_Svc -->|Fast Coaching / LLM| AIGW
    RT_Svc -->|Frame State & Locks| Redis_Store

    Worker_Svc -->|Dequeue ARQ| Redis_Store
    Worker_Svc -->|Embeddings & Extract| Supabase_PG
    Worker_Svc -->|Fetch / Store| S3_Buckets

    AIGW --> RemoteLLM
```

---

## 2. Workload & Service Breakdown

| Workload / Service | Technology | Runtime Characteristics | Statefulness | Scalability Model |
| :--- | :--- | :--- | :--- | :--- |
| **Web Dashboard** | Next.js 15, React 19 | Serverless Edge / Node SSR, 15 static routes | Stateless | Autoscaled on Edge |
| **Desktop Arena** | Electron 28, Vite, React | Client-side native audio loopback & renderer | Local state | N/A (Desktop binary) |
| **REST Core (`praxis-api`)** | FastAPI, Python 3.11, Uvicorn | High-concurrency I/O bound, async DB pool | Stateless | Cloud Run (0 to 10 instances) |
| **Realtime Agent (`praxis-realtime`)** | FastAPI WebSocket, Python 3.11 | High CPU/Memory (faster-whisper, silero-vad) | Stateful (per WS connection) | Cloud Run (1 to 5 instances, min 1) |
| **Background Worker (`praxis-worker`)** | ARQ, Python 3.11 | Asynchronous queue consumer, batch processing | Stateless worker | Continuous container (1 to 3 instances) |
| **AI Gateway** | Python package (`praxis_ai_gateway`) | In-process library with Redis budget guards | Stateless | Shared within API, RT, and Worker |
| **Primary Database** | Supabase PostgreSQL 15/16 | Relational data, pgvector embeddings, RLS | Highly Stateful | Managed Supabase with Read Replicas |
| **Cache & Task Broker** | Redis 7 | Task queues, sliding-window rate limits, locks | Semi-Persistent | Managed Redis with AOF persistence |
| **Document Storage** | Object Storage / S3 | Immutable PDF/DOCX resumes, debrief exports | Persistent | Multi-region private buckets |

---

## 3. Infrastructure Dependencies & Failure Domains

### 3.1 Failure Domain 1: External AI Model Providers
- **Potential Risk**: Provider rate-limiting (429), latency spikes, network timeouts, or full outages from OpenRouter, DeepSeek, or Gemini.
- **Implemented Protection**: Multi-provider fallback chain, circuit breakers tripping to `OPEN` after 5 consecutive failures, exponential backoff, and local Flan-T5/deterministic scoring fallback.

### 3.2 Failure Domain 2: Realtime WebSocket Audio Bottlenecks
- **Potential Risk**: Candidate audio processing overload on CPU-intensive STT transcription.
- **Implemented Protection**: faster-whisper small model loaded offline into memory (`HF_HUB_OFFLINE=1`), VAD pre-filtering out non-speech frames, 18-byte monotonic binary framing (`>BBIdI`), and 100-item drop-oldest ring buffers.

### 3.3 Failure Domain 3: Database Connection Starvation
- **Potential Risk**: Connection spikes caused by autoscaled Cloud Run instances exceeding PostgreSQL connection limits.
- **Implemented Protection**: Pinned connection budget (`DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=3`) per container instance with `pool_pre_ping=True` and pool recycle after 1800s. Maximum 10 instances consume $\le 50$ connections out of 100 available connections.

### 3.4 Failure Domain 4: Asynchronous Queue Backlog
- **Potential Risk**: Sudden bursts of resume uploads or scheduled debrief jobs stalling worker processing.
- **Implemented Protection**: Idempotency locks in Redis, bounded worker retries (`WORKER_MAX_TRIES=3`), job timeouts (`WORKER_JOB_TIMEOUT_S=300`), and dead-letter queue routing.

---

## 4. Current Implementation Status

| Component | Architecture Role | Repository Path | Implementation State |
| :--- | :--- | :--- | :---: |
| **REST API** | Core business logic & auth | `backend/app/` | **IMPLEMENTED & DEPLOYABLE** |
| **Realtime Service** | WebSocket speech processing | `realtime-agent/` | **IMPLEMENTED & DEPLOYABLE** |
| **Background Worker** | Async document & debrief tasks | `backend/app/worker_tasks.py` | **IMPLEMENTED & DEPLOYABLE** |
| **AI Gateway** | Unified LLM routing & budgets | `packages/ai-gateway/` | **IMPLEMENTED & DEPLOYABLE** |
| **Web Application** | Candidate dashboard | `apps/web/` | **IMPLEMENTED & BUILT** |
| **Desktop Client** | Live practice application | `apps/desktop/` | **IMPLEMENTED & BUILT** |
| **Database Migrations** | 71 tables, RLS, pgvector | `supabase/migrations/` | **100% IDEMPOTENT & VERIFIED** |
| **GCP Terraform** | Cloud Run, VPC, IAM, Secrets | `infra/gcp/` | **VALIDATED (`terraform validate`)** |
| **CI/CD Automation** | Test, build, push, deploy | `cloudbuild.yaml`, `.github/` | **CONFIGURED & TESTED** |
