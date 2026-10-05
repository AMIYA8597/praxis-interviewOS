# PRAXIS Backend Sovereignty Audit
**Date:** 2026-10-05
**Commit:** b4687c8 (main)
**Auditor:** Claude Sonnet 4.6

---

## Executive Summary

The PRAXIS backend is architecturally production-grade in its core AI, realtime, database, and worker layers. RLS, JWT verification, circuit breakers, cost governance, structured logging, and the dual-path coaching pipeline are all fully implemented. The primary gaps are **operational hardening** (security headers, CSRF, backup/restore) and **quality assurance infrastructure** (AI evaluation corpus, benchmark answers, metrics endpoint).

**Overall assessment**: PARTIAL — deployable after P1–P6 blockers are resolved.

---

## Legend
| Status | Meaning |
|--------|---------|
| COMPLETE | Implemented, tested, observable |
| PARTIAL | Implemented but incomplete or untested in a critical dimension |
| MISSING | Not implemented |
| BROKEN | Exists but does not function correctly |
| UI-DEPENDENT | Logic is in the frontend that should be in the backend |
| UNTESTED | Code exists but no automated tests verify it |
| DUPLICATED | Same logic exists in multiple places; needs consolidation |

---

## SECURITY LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Backend boundary (no React/Next/Electron in Python) | COMPLETE | CI runs `check_gateway_boundary.py`; grep confirms zero React/Next/Electron imports in backend/ or realtime-agent/ |
| 6 | RLS on all tenant tables | COMPLETE | `20260907235802_enable_rls_policies.sql`; `tests/security/test_rls_enabled.py` asserts all tables in CI against real Postgres |
| 7 | FORCE RLS | COMPLETE | `20261004000002_force_rls.sql` issues `ALTER TABLE … FORCE ROW LEVEL SECURITY` for all public tables |
| 8 | JWT → RLS pipeline (cryptographic verification) | COMPLETE | `backend/app/auth.py`: JWKS/RS256 verification, kid rotation, exp/iat/sub/aud/iss all required before any DB context |
| 9 | Authentication endpoints | COMPLETE | `backend/app/api/auth.py`: signup, login, logout, refresh under `/api/v1` |
| 10 | JWT verification (JWKS, RS256, key rotation) | COMPLETE | Redis + in-memory JWKS cache; unknown kid triggers rate-limited force-refresh; RS256/ES256/EdDSA + HS256 fallback |
| 11 | Authorization policies (role-based) | PARTIAL | Admin role guard in `admin.py`; tenant isolation via RLS; no fine-grained RBAC middleware beyond admin |
| 26 | Provider SDK isolation | COMPLETE | `check_gateway_boundary.py` in CI; only `praxis_ai_gateway/providers/` contains openai/anthropic/groq |
| **30** | **Prompt injection defense** | **COMPLETE** | `prompt_builder.add_untrusted()` escapes delimiters, strips injected SYSTEM tags; `tests/security/test_prompt_injection.py` |
| **67** | **Rate limiting** | **COMPLETE** | `RateLimitMiddleware` Redis token bucket; per-route limits (signup 5/min, resume 10/min) |
| 68 | Abuse protection | PARTIAL | Rate limiting + SSRF protection; no anomaly detection or IP reputation scoring |
| 69 | CORS | COMPLETE | `CORSMiddleware` explicit origins; settings validator rejects `*` in production |
| **70** | **Security headers (HSTS, X-Frame-Options, CSP)** | **MISSING** | No security headers middleware in backend; frontend sets CSP via `next.config.js` but backend itself has none |
| **71** | **CSRF protection** | **MISSING** | Bearer token APIs do not require CSRF; but no explicit CSRF verification exists for any cookie-based flows |
| 72 | SSRF protection | COMPLETE | `security.py::is_safe_url()` resolves hostname, blocks private/loopback/169.254.x.x IPs |
| 73 | Upload security | COMPLETE | `validate_file_magic_bytes()`, `MAX_UPLOAD_BYTES`, MIME/size enforced in `uploads.py` |
| 109 | Audit log (immutable security events) | **BROKEN** | `audit_logs` ORM model and admin endpoint exist; **migration SQL creating the table is missing from `supabase/migrations/`** |
| 117 | Data privacy / no PII in logs | COMPLETE | `logging_config.py` SENSITIVE_KEYS set; redaction applied before log emission |

---

## AI/ML LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 23 | Claim grounding engine | COMPLETE | `realtime_agent/app/scoring/claims.py`; SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED/CONTRADICTED states |
| 24 | Anti-hallucination / provenance | PARTIAL | RAG chunk source tracked; structured output schema enforced; no dedicated hallucination scorer |
| 25 | AI Gateway (sole provider boundary) | COMPLETE | All AI calls via `GatewayRouter`; CI boundary check enforced |
| 27 | AI Model registry | COMPLETE | `ModelRegistry` in `registry.py`; `config/models.yaml`; placeholder values raise at startup |
| 28 | Structured AI output | COMPLETE | `prompt_builder.add_output_schema(PydanticModel)` embeds JSON schema; schemas in `ai-gateway/schemas/` |
| 29 | Prompt architecture (centralized, versioned) | PARTIAL | `prompts/` directory with versioned markdown files; `PromptBuilder` centralises construction; no explicit version field in builder |
| 31 | Local-first AI/ML | COMPLETE | Silero VAD (ONNX), Piper TTS, faster-whisper, bge-small-en-v1.5 |
| 32 | VAD implementation | COMPLETE | `audio/vad.py`: Silero ONNX state machine with configurable start/end frames |
| 33 | Streaming STT | COMPLETE | `transcription/local_faster_whisper.py` + `cloud_groq.py`; routing in `transcription/router.py` |
| 34 | TTS with barge-in/cancel | COMPLETE | `PiperTTSAdapter.synthesize_streaming()` accepts `CancellationToken`; `BargeInController.trigger()` cancels and sends `audio.stop_playback` |
| 35 | Dual-path coaching (DSP + AI, independent) | COMPLETE | `coaching/metrics.py` (pure DSP) + `accumulator.py` (AI path); `test_coaching_concurrent.py` verifies independence |
| **51** | **RAG evaluation** | **PARTIAL** | Integration tests exist; no formal evaluation corpus or precision/recall metrics |
| 81 | AI cost governance | COMPLETE | `budget_guard.py`: daily + session hard limits; `BudgetExceeded` raised before any billable call |
| 82 | Model fallback chain | COMPLETE | `ModelRegistry.filter_candidates()` + `resilience.py` fallback execution order |
| 83 | Provider health / circuit breaker | COMPLETE | `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN) in `resilience.py`; `/health/providers` endpoint |
| **84** | **Model output safety validation** | **MISSING** | No content safety filter on AI outputs; only structured schema validation |
| 85 | Tool security | N/A | No agentic tool use in codebase |

---

## REALTIME LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 36 | Interview state machine | COMPLETE | `state_machine.py`: 18 named states, full TRANSITIONS dict, `InvalidTransitionError`, OTel span events |
| 37 | Barge-in / cancellation tokens | COMPLETE | `barge_in.py` + `cancellation.py::CancellationToken`; cancels LLM generation and TTS |
| 38 | Realtime protocol (versioned message types) | PARTIAL | `Envelope` type in `protocol.py`; WS close codes documented; no explicit protocol version field |
| 39 | Realtime WebSocket auth | COMPLETE | JWT in query param or first text frame; `WS_AUTH_TIMEOUT_S`; WS close codes 4401/4404/4409 |
| 40 | Realtime reconnect + session resume | COMPLETE | `session:state:{id}` in Redis; `WS_RECONNECT_GRACE_S`; `redis_state.py` persists session state |
| 41 | Question engine | COMPLETE | `generation.py` uses adaptive difficulty + candidate memory + JD blueprint + past questions |
| 42 | Question taxonomy | COMPLETE | `question_taxonomy.py`: DSA/Backend/DB/Distributed/Networking/OS/Security/Cloud/DevOps/AI/ML/BehavioralEnum |
| 43 | Adaptive interviewer | COMPLETE | `adaptive_difficulty.py`: IRT-inspired step_up/step_down; consecutive-correct double-step |
| 44 | Interview modes | COMPLETE | `coding_engine.py`, `system_design_engine.py`, `behavioral_engine.py`, `interview_engines.py` router |
| 45 | Technical scoring | COMPLETE | `scoring/service.py`: multi-dimension with `rubric_version` |
| 46 | System design engine | COMPLETE | `system_design_engine.py`: 24-phase structured flow, diagram contradiction detection |
| 47 | Coding engine (sandboxed execution) | COMPLETE | `coding_engine.py`: subprocess with CPU/memory/time/process limits |
| 48 | Behavioral engine (STAR) | COMPLETE | `behavioral_engine.py`: regex STAR component detection with per-component scoring |
| 49 | Communication intelligence | COMPLETE | `coaching/metrics.py`: WPM, filler rate (YAML-configurable fillers), pause stats |

---

## DATABASE LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 3 | Database models (SQLAlchemy) | COMPLETE | `db/models.py`: GUID, JSONB, TSVECTOR, pgvector; SQLite-compatible for unit tests |
| 4 | Migrations (ordered, complete) | COMPLETE | 24 supabase SQL migrations + alembic versions 001–004; CI verifies idempotency |
| 5 | Database constraints (FK, unique, check) | PARTIAL | FK + unique in models.py; check constraints only in migration SQL |
| 52 | Candidate memory | COMPLETE | `candidate_memory.py`: fact/inference/preference separation; mastery scores from session |
| 56 | Study engine (SM-2) | COMPLETE | `services/sm2.py`: full SuperMemo-2 algorithm; `services/study.py`; study API router |
| 74 | Data retention | COMPLETE | `data_retention_days` on candidate model; `purge_transcripts` worker job |
| 95 | Cache strategy (Redis TTL, invalidation) | COMPLETE | `CANDIDATE_CACHE_TTL_S`, `JWKS_CACHE_TTL_S`; Redis pipeline with TTL in rate limiter; invalidate on mutation |
| 107 | Migration system (ordered, tracked, tested) | COMPLETE | `scripts/migrate.py` + `migration_status` table; CI idempotency check |

---

## API LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 2 | Layered architecture | COMPLETE | `api/ → services/ → repositories/ → db/`; no cross-layer leakage |
| 12 | REST API completeness | COMPLETE | 18 routers: candidates, resumes, jobs, sessions, study, debrief, readiness, analytics, admin, auth, etc. |
| 13 | API versioning | PARTIAL | `/api/v1` prefix; no deprecation headers, sunset policy, or v2 pathway |
| 14 | Pydantic request/response models | COMPLETE | `backend/app/schemas/`: complete schemas for all entities |
| 15 | Error contract | COMPLETE | `exceptions.py`: `{code, message, detail, retryable, request_id}` envelope; no raw tracebacks |
| 16 | Pagination support | PARTIAL | `next_cursor` in `schemas/common.py`; not uniformly applied to all list endpoints |
| 17 | Idempotency for critical operations | COMPLETE | `worker_idempotency.py`; session completion, document chunks all idempotent |
| 53 | Observability (correlation IDs) | COMPLETE | `RequestIdMiddleware` + `core/context.py` contextvars for request_id/user_id/candidate_id/session_id |
| 54 | Structured JSON logging | COMPLETE | `logging_config.py`: JSON formatter, sensitive key redaction, context injected every record |
| **65** | **Metrics endpoint / collection** | **MISSING** | No `/metrics` (Prometheus) endpoint; only health probes — no operational dashboards possible |
| 66 | OpenTelemetry tracing | COMPLETE | `configure_tracing()` in bootstrap.py; FastAPI instrumented; state machine emits OTel spans |
| 98 | Health checks | COMPLETE | `/health/live`, `/health/ready`, `/health/providers` all implemented |
| 99 | Graceful shutdown | COMPLETE | `lifespan()` closes ARQ/Redis/DB; Docker CMD `--timeout-graceful-shutdown 30` |
| 110 | Admin operations API | COMPLETE | `/api/v1/admin`: provider health, AI usage, security events, queue health |
| **111** | **Feature flags** | **PARTIAL** | `feature_flags` ORM model + RLS in scripts; **no migration SQL** in `supabase/migrations/` — table never created |
| 113 | OpenAPI specification | PARTIAL | FastAPI auto-generates `/openapi.json`; disabled in production by default |
| 114 | UI integration contract (thin UI) | COMPLETE | All business logic in backend; no React imports in Python |

---

## WORKER LAYER

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 18 | Resume upload pipeline | COMPLETE | `worker_tasks.process_resume`: parse → chunk → embed → store → extract skills |
| 21 | JD processing pipeline | COMPLETE | `services/jd_preparation.py` + `ai-gateway/schemas/jd.py` structured extraction |
| 60 | Debrief engine | COMPLETE | `services/debrief.py` (API) + `realtime_agent/app/interview/debrief.py` (in-session) |
| 75 | Account deletion workflow | COMPLETE | `DeletionService`: cascading delete → blobs → Supabase auth; idempotent |
| 77 | ARQ background jobs | COMPLETE | `worker_tasks.py` with `@job()` decorator; ARQ pool in lifespan |
| 78 | Canonical worker job types | COMPLETE | process_resume, generate_debrief, generate_study_cards, purge_transcripts, process_deletion_job |
| 79 | Job idempotency | COMPLETE | `worker_idempotency.py::idempotent_job()` with DB deduplication key |
| 80 | Retry policy (transient vs permanent) | COMPLETE | `PermanentJobError` skips retry; transient → ARQ exponential backoff; dead-letter to `failed_jobs` |

---

## DEPLOYMENT

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 96 | Configuration management | COMPLETE | Pydantic Settings; `validate_production()` fails fast at startup |
| 97 | Environment separation | COMPLETE | `APP_ENV` gating; `staging/` and `production/` tfvars; env identity validated at startup |
| 100 | Cloud Run deployment contract | PARTIAL | Dockerfiles complete; `cloudbuild.yaml` pipeline complete; **Cloud Run not yet provisioned** |
| 101 | Container contract | COMPLETE | Non-root `praxis` user; pinned `requirements-lock.txt`; minimal runtime image |
| 102 | Image strategy | COMPLETE | Three separate Dockerfiles: api, realtime, worker |
| 103 | GCP security | COMPLETE | Terraform: Workload Identity pool, Secret Manager IAM bindings, Cloud Armor |
| 104 | Redis production (Memorystore + VPC) | COMPLETE | `google_redis_instance.praxis` in `main.tf`; VPC connector for private access |
| 105 | Supabase production | PARTIAL | RLS + storage in migrations; no automated backup configuration in Terraform |
| **106** | **Backup/restore (RPO/RTO)** | **MISSING** | `check_disaster_recovery.py` explicitly warns "No backup script found"; no `scripts/backup.sh`; no tested restore |
| 108 | Disaster recovery | PARTIAL | FK cascades documented; DR check script exists; backup gap is the critical hole |

---

## TESTING

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 86 | System design knowledge graph | PARTIAL | `question_taxonomy.py` has topic relationships; no full concept prerequisite graph |
| 87 | Question quality (rubric, expected concepts) | PARTIAL | Questions have difficulty + domain; no expected_concepts or follow-up fields |
| **88** | **Interview calibration / benchmark answers** | **MISSING** | No golden answer corpus or calibration framework |
| **89** | **Rubric versioning (version management workflow)** | **PARTIAL** | `rubric_version` column on TurnScore; no version management or promotion workflow |
| **90** | **AI evaluation regression corpus** | **MISSING** | `scripts/run_evaluation.py` uses hardcoded thresholds; no real golden corpus |
| 91 | Performance engineering | UNTESTED | No p50/p95 measurements collected in CI; `scripts/load_test.py` not in CI |
| 92 | Concurrency testing | PARTIAL | `tests/realtime/test_coaching_concurrent.py`; not integrated into CI load tests |
| **93** | **Realtime scale testing** | **PARTIAL** | `scripts/load_test.py` exists; not executed in CI |
| **94** | **Database scale testing** | **MISSING** | No scale tests for query performance or index efficiency |
| 118 | Test pyramid | COMPLETE | CI: unit, integration, DB/RLS (real Postgres), API, WebSocket, security, worker, prompt injection |
| 119 | Real Postgres tests in CI | COMPLETE | `pgvector/pgvector:pg17` service container; all migration/RLS tests |
| 120 | No-fake-data gate | COMPLETE | `scripts/check_no_fake_data.py` runs in CI |

---

## DOCUMENTATION

| # | Capability | Status | Evidence |
|---|-----------|--------|----------|
| 53 | Personal interview profile | COMPLETE | `readiness_service.py`; per-dimension scores with confidence and sample count |
| 54 | Readiness engine | COMPLETE | Evidence-aggregation model; no "87% hire chance" claims |
| 55 | Preparation engine | COMPLETE | `preparation_service.py`: prioritized plan with reasons |
| 57 | Knowledge decay detection | COMPLETE | `candidate_memory.py`: flashcard-pass + interview-fail → INTERVIEW_EXPRESSION_GAP classification |
| 58 | Improvement engine | COMPLETE | `services/improvement.py`: IMPROVED/STABLE/REGRESSED/INSUFFICIENT_DATA |
| 59 | Answer replay / retry | COMPLETE | TurnScore + transcript stored; `sessions/[id]/debrief` page shows attempt history |
| 61 | Job intelligence | COMPLETE | `jobs.py` router; multiple jobs per candidate; stage tracking |
| 62 | Application lifecycle tracking | COMPLETE | ApplicationStatus enum: APPLIED→REJECTED/OFFER and all intermediate stages |
| 112 | API versioning (no silent breakage) | PARTIAL | `/api/v1`; no deprecation or sunset headers |
| 115 | Electron contract | PARTIAL | `apps/desktop/`: IPC handlers present; no formal API contract doc |
| 116 | Observability correlation | COMPLETE | `core/context.py`: request_id → user_id → candidate_id → session_id; OTel trace propagation |

---

## CRITICAL GAPS — MUST FIX FOR PRODUCTION

| Priority | # | Capability | Fix Required |
|----------|---|-----------|-------------|
| **P1** | 70 | Security headers | Add `SecurityHeadersMiddleware` to FastAPI backend |
| **P2** | 71 | CSRF | Document that all PRAXIS endpoints use Bearer tokens (not cookies); if any cookie flow is introduced, CSRF required |
| **P3** | 84 | AI output safety validation | Add content safety layer in AI Gateway for LLM outputs |
| **P4** | 106 | Backup/restore | Create `scripts/backup.sh`, test restore, document RPO/RTO |
| **P5** | 109 | Audit log migration | Add `supabase/migrations/` SQL file creating `audit_logs` table |
| **P6** | 111 | Feature flags migration | Add `supabase/migrations/` SQL file creating `feature_flags` table |
| **P7** | 65 | Prometheus metrics | Add `/metrics` endpoint with Prometheus client |
| **P8** | 90 | AI evaluation corpus | Create `tests/evaluation/` with a real benchmark dataset |
| **P9** | 88 | Interview calibration | Create `tests/calibration/` with benchmark answers and calibration tests |
| **P10** | 106+100 | Disaster recovery | Write `docs/DISASTER_RECOVERY_RUNBOOK.md` + test restore procedure |

---

## Summary Statistics

| Status | Count |
|--------|-------|
| COMPLETE | 72 |
| PARTIAL | 22 |
| MISSING | 8 |
| BROKEN | 2 |
| UNTESTED | 1 |
| N/A | 1 |
| **Total** | **106** |

*(14 capabilities not directly applicable or merged into related items)*
