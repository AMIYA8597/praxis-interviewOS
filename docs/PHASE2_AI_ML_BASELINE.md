# PRAXIS InterviewOS — Phase 2 AI/ML Baseline & Gap Audit

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Base Branch**: `phase1-backend-db` (Checkpoint `e9b9533` / `33f837e`)  
**Target Branch**: `phase2-ai-ml`  
**Classification**: STAGE 0 BASELINE AUDIT — COMPLETE

---

## 1. Executive Summary

Phase 1 established an independently verifiable, production-grade backend and database architecture:
- 31 PostgreSQL production migrations with complete Row Level Security (`FORCE RLS`) on all tenant tables.
- 75/75 Backend Completeness Gate passed (`scripts/check_backend_completeness.py`).
- 15/15 Final Quality Gate passed (`scripts/final_quality_gate.py`).
- Cloud Supabase project `rqbbfegkqmsvthdgoyqk` (`Central EU - Frankfurt`) verified live with publishable and secret keys.
- Monorepo test suites all green across 305+ unit, integration, and security tests.

Phase 2 builds the production AI/ML Intelligence Engine on top of this authoritative foundation without regressions, duplicate databases, or mock transcripts.

---

## 2. Test Suite Baseline Inventory

Every test suite was executed against the local environment and recorded:

| Suite | Scope | Passed | Skipped | Failed | Execution Time |
|---|---|---|---|---|---|
| `backend/tests` | FastAPI endpoints, DB repositories, auth, security, workers | 184 | 1 | 0 | ~101s |
| `packages/ai-gateway/tests` | Provider adapters, router, budget guard, circuit breaker | 19 | 0 | 0 | ~5s |
| `realtime-agent/tests` | WebSocket lifecycle, state machine, VAD, TTS, dual-path | 32 | 0 | 0 | ~60s |
| `tests/` | RLS isolation, cascades, storage, full spoken turn | 36 | 3 | 0 | ~80s |
| `@praxis/ui` | Shared UI components | 20 | 0 | 0 | ~19s |
| `apps/desktop` | Electron renderer, audio capture, coaching HUD | 15 | 0 | 0 | ~12s |
| **Total** | **All Monorepo Test Suites** | **306** | **4** | **0** | **Green** |

*Note on skips*: The 4 skipped tests require optional external infrastructure (live pgvector extension on local host, live external Redis TTL daemon, live cloud transcription provider key). None hide code defects.

---

## 3. Realtime Protocol & Audio Contract Verification

- **Frame Format**: Strict 18-byte binary header (`>BBIdI`):
  - `proto_ver` (uint8 = 1)
  - `frame_type` (uint8 = 1 for audio)
  - `client_seq` (uint32)
  - `capture_ts` (float64)
  - `payload_len` (uint32)
  - Followed by raw 16kHz mono 16-bit little-endian PCM samples (`int16`).
- **Binary Header Unpack & Validation**: Fully covered in `realtime-agent/tests/test_audio_frame.py` and `test_audio_protocol.py`.
- **Fast Path vs Slow Path Independence**:
  - Fast Path: Audio activity detection via Silero VAD, client sequence tracking, speaking duration, cadence metrics via `CoachingMetricsAccumulator`. Strictly non-blocking using `asyncio.sleep` (validated in `test_coaching_path_nonblocking_under_llm_delay.py`).
  - Slow Path: Asynchronous question generation, answer scoring, claim extraction, and debrief generation.

---

## 4. Supabase Cloud Integration

- **Project Ref**: `rqbbfegkqmsvthdgoyqk`
- **Region**: Central EU (Frankfurt) — `eu-central-1`
- **Status**: Healthy
- **Project URL**: `https://rqbbfegkqmsvthdgoyqk.supabase.co`
- **Publishable Key**: `sb_publishable_QL_4JQu66AfBg0aDyEDuig_PSYexNvF`
- **Secret Key**: `sb_secret_...[REDACTED_SERVICE_ROLE_KEY]` (Verified HTTP 200 against PostgREST endpoint)
- **Local Database**: PostgreSQL 18 on `localhost:5432/praxis` with 71 public tables and 31 migrations applied.

---

## 5. Workstream Gap Analysis & Action Plan

| Workstream | Current Repository State | Target Phase 2 Requirement | Gaps to Implement |
|---|---|---|---|
| **A: Audio Intelligence** | Basic Silero VAD + Whisper router in `realtime_agent/app/audio/` | Live 2-vCPU faster-whisper RTF benchmark, real WAV test corpus (clean, accented, noisy, fast), degraded mode fallback | Automated audio evaluation dataset (`ai-evaluation/datasets/audio/`), RTF measurement script |
| **B: Candidate Context** | Resume parsing & basic facts in `candidate_memory.py` | Provenance tracking (exact chunk & character offset), verified vs unverified facts, JD requirement matching | Fact extraction model with source span attribution |
| **C: Production RAG** | Hybrid retrieval in `praxis_ai_gateway/retrieval.py` | pgvector cosine similarity + tsvector BM25 hybrid search, tenant isolation, NDCG/MRR evaluation | RAG benchmark suite with synthetic corpus |
| **D: Question Engine** | Dynamic question generation in `generation.py` | Adaptive follow-ups, cognitive depth modulation, JD coverage tracking | Domain question matrix and difficulty progression tests |
| **E: Answer Evaluation** | Calibrated scoring in `scoring/service.py` | Multi-dimensional rubrics, missing dimension handling (`null` + `measurement_status`), human-reviewed calibration benchmark | 50-answer evaluation dataset across 6 archetypes |
| **F: Claim Grounding** | Binary claim checking in `scoring/claims.py` | 5-tier classification (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`), source chunk provenance | Claim classifier upgrading from binary to 5-tier schema |
| **G: Coding Intelligence** | AST analysis & sandbox execution in `coding_engine.py` | Multi-language test runner (Python, TypeScript, SQL), algorithmic complexity detection, memory/time limits | Hidden test execution and adversarial protection tests |
| **H: System Design** | Rubric evaluator in `system_design_engine.py` | Architecture dimension scoring (trade-offs, bottleneck identification, scalability) | Complete calibration test suite |
| **I: Behavioral** | STAR model evaluation in `behavioral_engine.py` | STAR dimension completeness (Situation, Task, Action, Result) with quantitative evidence requirements | 15-case behavioral calibration verification |
| **J: Realtime Coaching** | Dual-path orchestrator in `orchestrator.py` | Sub-100ms fast path under heavy slow-path LLM delay, turn resumption | Benchmarked event timing and latency proof |
| **K: Debrief & Readiness** | Debrief aggregation in `debrief.py` | Evidence-grounded "PRAXIS Readiness Estimate", study plan generation, uncertainty exposure | Calibrated readiness confidence scoring |
| **L: Model Orchestration** | Gateway router & budget guard in `praxis_ai_gateway/` | Task routing, latency tiering, fallback chain, model registry metadata | Complete provider catalog and token budget enforcement |
| **M: Datasets & Research** | Distributed across test folders | Organized `ai-evaluation/` directory with benchmark datasets | Centralized benchmark execution runner |
| **N: Observability & MLOps** | Structured logging & OTEL traces | Prompt versioning, inference latency metrics, cost attribution | Phase 2 MLOps runbook |

---

## 6. Stage 0 Acceptance Gate

- [x] Phase 1 contracts preserved (database schema, RLS, auth, API).
- [x] All 306 monorepo tests passing.
- [x] Realtime audio contract validated.
- [x] Cloud Supabase configuration validated.
- [x] Quality gates (15/15) and backend completeness (75/75) 100% green.
- [x] Baseline report published to `docs/PHASE2_AI_ML_BASELINE.md`.
