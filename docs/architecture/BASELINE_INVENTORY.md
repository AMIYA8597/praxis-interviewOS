# PRAXIS InterviewOS — Repository Inventory & Baseline Audit Report

**Document ID**: REPO-BASELINE-001  
**Milestone**: Four-Phase Engineering Rebuild — Part 0.2  
**Date**: 2026-11-01  
**Base Commit**: `22c5325`  
**Active Working Branch**: `four-phase-rebuild`  
**Standard**: Antigravity Pro Global Engineering Contract (Section 0)  

---

## 1. Executive Summary & Inventory Overview

PRAXIS InterviewOS is a production-oriented, AI-powered interview preparation, practice, coaching, and assessment platform. This repository baseline report documents the current codebase structure, package relationships, existing verified implementations, traced user journeys, and technical invariants before initiating the four-phase sequential rebuild.

The codebase is organized as a unified monorepo containing:
1. **`backend/`**: FastAPI REST API, asynchronous ARQ worker tasks, SQLAlchemy async models (42 models), business services, security middlewares, and automated test harnesses.
2. **`realtime-agent/`**: Independent, decoupled FastAPI realtime agent dedicated to low-latency binary WebSocket audio frame ingestion (`>BBIdI`), Silero VAD, faster-whisper speech recognition, and coaching metrics.
3. **`packages/ai-gateway/`**: Vendor-neutral AI Gateway encapsulating LLM provider adapters (OpenAI, Gemini, DeepSeek, Anthropic, Groq, Ollama), 3-state circuit breakers, atomic Redis token budget guards, and hybrid RAG embedding retrieval.
4. **`packages/ui/`**: Shared React design system containing 14 tested component modules with strict accessibility compliance.
5. **`packages/config/`**: Centralized Pydantic `Settings` enforcing strict environment configuration, database connection budgets, and CORS policies.
6. **`apps/web/`**: Next.js 15 App Router web client providing complete candidate dashboards, resume processing, and interview session interfaces.
7. **`apps/desktop/`**: Electron desktop client utilizing context isolation, disabled Node integration, and DPAPI-backed secure credential storage.
8. **`supabase/`**: 31 sequential database migrations with strict Row-Level Security (RLS) and FORCE RLS policies.
9. **`infra/`**: Google Cloud Platform Terraform infrastructure (`infra/gcp/` and `infra/bootstrap/`) targeting `asia-south1`.

---

## 2. Directory Structure & Module Inventory

```text
interviewOS/
├── .github/workflows/          # CI/CD pipelines (GitHub Actions + Cloud Build triggers)
├── apps/
│   ├── desktop/                # Electron Windows 11 Desktop Client
│   │   ├── src/main/           # Main process (audio capture, IPC handlers, safeStorage)
│   │   ├── src/preload/        # Isolated context bridge (electronAPI)
│   │   ├── src/renderer/       # React HUD, Arena, and diagnostic components
│   │   └── tests/              # Jest unit & IPC security tests (15/15 PASS)
│   └── web/                    # Next.js 15 Web Application (App Router)
│       ├── app/                # Protected routes (dashboard, resumes, sessions, study)
│       └── components/         # Web-specific presentation components
├── backend/                    # Core REST API & Background Workers
│   ├── app/
│   │   ├── api/                # 20 versioned REST route controllers
│   │   ├── core/               # Tracing, logging, security guards, DB engine, queue
│   │   ├── db/                 # 42 SQLAlchemy relational models & session maker
│   │   ├── repositories/       # Data access objects with candidate scoping
│   │   ├── schemas/            # Pydantic v2 request/response contracts
│   │   ├── services/           # Core domain logic (scoring, study, coding, memory)
│   │   └── workers/            # Ingestion, cleanup, and background tasks
│   └── tests/                  # Security (63), Hardening (55), Production (6) test suites
├── packages/
│   ├── ai-gateway/             # Multi-provider AI Gateway with Circuit Breakers
│   ├── config/                 # Pydantic Settings & environment validators
│   └── ui/                     # Shared Design System (28/28 Jest PASS)
├── realtime-agent/             # WebSocket Audio & Realtime Speech Engine
│   └── realtime_agent/app/
│       ├── audio/              # Silero VAD & faster-whisper integration
│       ├── coaching/           # Fast-path DSP pacing & filler metrics
│       ├── interview/          # State machine, turn detection & policy
│       ├── scoring/            # Claim grounding & rubric evaluation
│       └── session/            # Session manager & Redis state store
├── infra/                      # Terraform Infrastructure as Code
│   ├── bootstrap/              # State bucket & KMS key provisioning
│   └── gcp/                    # Cloud Run, Memorystore Redis, VPC Connector
└── supabase/migrations/        # 31 SQL migrations with RLS & FORCE RLS
```

---

## 3. End-to-End User Journey Tracing

### Journey 1: Candidate Registration & Authentication
- **Entry**: Client requests `/auth/v1/signup` or login via Supabase Auth.
- **Backend Flow**: Asymmetric RS256 JWT issued with `authenticated` audience. `backend/app/auth.py` validates JWT against cached JWKS (`.well-known/jwks.json`).
- **Database**: PostgreSQL automatically maps `auth.uid()` to `public.candidates` table via RLS policy `candidates_candidate_isolation_select`.
- **Status**: **PASS** (15/15 JWT hardening tests passing).

### Journey 2: Resume Ingestion & Candidate Fact Grounding
- **Entry**: Candidate uploads PDF/DOCX via `POST /api/v1/resumes/upload`.
- **Validation**: `backend/app/api/resumes.py` verifies file signature via python-magic, enforces 10MB limit, strips path traversal payloads.
- **Worker Flow**: Dispatches `parse_resume_task` via ARQ Redis queue. Worker extracts text, sections, dates, and claims.
- **RAG Embedding**: Chunks embedded via `BAAI/bge-small-en-v1.5` into `document_chunks`. Crucial invariant: chunks require `verified_by_user = true` before inclusion in interview question generation.
- **Status**: **PASS**.

### Journey 3: Realtime Interview Session & Audio Ingestion
- **Handshake**: WebSocket connects to `/ws/interview/{session_id}`. Client sends JSON authentication frame within 10 seconds.
- **Audio Framing**: 18-byte binary header (`>BBIdI`: version, type, sequence, timestamp, payload length) followed by mono PCM16 16kHz audio.
- **Fast Path**: Realtime agent processes audio through Silero VAD and faster-whisper in-memory model. Partial transcripts and pacing metrics stream to Desktop Coaching HUD at $<80\text{ ms}$ cadence.
- **Slow Path**: Utterance completion (silence $\ge 500\text{ ms}$) triggers final transcript assembly, context retrieval from PostgreSQL, and LLM evaluation via AI Gateway.
- **Status**: **PASS** (Protocol, VAD, and STT benchmarks verified).

### Journey 4: Debrief Scoring & Spaced Repetition Study Plan
- **Completion**: Session transitions to `COMPLETED`. Realtime agent aggregates turn scores and claim grounding states (`SUPPORTED`, `CONTRADICTED`, `UNCERTAIN`).
- **Persistence**: Debrief persisted to `session_debriefs`. Weak skills automatically seeded into `study_items` using SuperMemo-2 (SM-2) spaced repetition algorithm.
- **Status**: **PASS**.

### Journey 5: Candidate Data Deletion (GDPR & Privacy Compliance)
- **Request**: Candidate triggers `DELETE /api/v1/candidates/me`.
- **Execution**: `backend/app/core/deletion.py` schedules idempotent cascade purging all resumes, audio segments, transcripts, scores, and embeddings.
- **Status**: **PASS** (Verified with automated deletion tests).

---

## 4. Technical Invariants & Rules

1. **No Fake Data Invariant**: Zero hardcoded mock results in runtime code. `scripts/check_no_fake_data.py` enforces this.
2. **Provider Isolation**: `import openai` is restricted to `packages/ai-gateway/praxis_ai_gateway/providers/openai.py`. `scripts/check_gateway_boundary.py` enforces this.
3. **Database Connection Pool Ceiling**: `DB_POOL_SIZE = 2`, `DB_MAX_OVERFLOW = 3` ensures maximum 75 concurrent connections across all autoscaling instances, strictly below the Supabase 100-connection threshold.
4. **Offline Speech Model Baking**: Whisper models are pre-cached in container image layers with `HF_HUB_OFFLINE = 1`, eliminating runtime network dependencies.
