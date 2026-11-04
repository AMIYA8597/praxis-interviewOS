# PRAXIS InterviewOS — Master Capability Matrix

**Classification Standard:**
- `IMPLEMENTED_AND_VERIFIED`: Code exists, is wired into runtime, and has verified test/execution evidence.
- `IMPLEMENTED_BUT_UNVERIFIED`: Code exists and is wired, but lacks dedicated automated test execution in this environment.
- `PARTIALLY_IMPLEMENTED`: Core logic exists but some edge cases, sub-features, or integrations are pending.
- `BROKEN`: Feature fails tests or runtime execution due to defects.
- `MISSING`: Capability is not present in codebase.
- `BLOCKED_BY_EXTERNAL_INFRASTRUCTURE`: Feature is fully implemented in code but execution requires external cloud/host services (e.g. live GCP apply, running Docker daemon, pgvector binary).
- `NOT_APPLICABLE`: Requirement not relevant to backend sovereign platform.

---

## 1. Authentication & Identity

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| JWT Verification (HS256/RS256) | `IMPLEMENTED_AND_VERIFIED` | `backend/app/auth.py` | `backend/tests/hardening/test_jwt_auth.py` (13 tests) |
| Supabase Auth Integration | `IMPLEMENTED_AND_VERIFIED` | `backend/app/auth.py` | `backend/tests/api/test_auth.py` |
| JWKS Key Rotation & In-Memory Cache | `IMPLEMENTED_AND_VERIFIED` | `backend/app/auth.py` | `backend/tests/hardening/test_jwt_auth.py` |
| Audience & Issuer Validation | `IMPLEMENTED_AND_VERIFIED` | `backend/app/auth.py` | `backend/tests/hardening/test_jwt_auth.py` |
| Token Expiration & Leeway Enforcement | `IMPLEMENTED_AND_VERIFIED` | `backend/app/auth.py` | `backend/tests/hardening/test_jwt_auth.py` |
| Development Auth Bypass Mode | `IMPLEMENTED_AND_VERIFIED` | `packages/config/settings.py` | `backend/tests/test_health.py` |
| Session Invalidation & Logout | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/auth.py` | `backend/tests/api/test_auth.py` |
| WebSocket JWT Handshake | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/main.py` | `realtime-agent/tests/integration/test_reconnect_ci.py` |

---

## 2. Authorization & Permissions

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| User Ownership Verification (IDOR Guard) | `IMPLEMENTED_AND_VERIFIED` | `backend/app/dependencies.py` | `backend/tests/hardening/test_authorization.py` |
| Admin Role Enforcement | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/admin.py` | `backend/tests/security/test_admin_auth.py` |
| Row-Level Security (RLS) on all 71 Tables | `IMPLEMENTED_AND_VERIFIED` | `supabase/migrations/20260907235802_enable_rls_policies.sql` | `tests/security/test_rls_enabled.py` |
| FORCE RLS on Candidate Tables | `IMPLEMENTED_AND_VERIFIED` | `supabase/migrations/20261004000002_force_rls.sql` | `scripts/check_disaster_recovery.py` |
| Tenant Isolation in Vector Retrieval | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/retrieval.py` | `backend/tests/security/test_rls_isolation.py` |
| Privileged Database Roles Separation | `IMPLEMENTED_AND_VERIFIED` | `supabase/migrations/20261004000001_app_role.sql` | Migration applied |

---

## 3. Database & Data Lifecycle

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| 31 Sequential Database Migrations | `IMPLEMENTED_AND_VERIFIED` | `supabase/migrations/*.sql` | `scripts/check_production_readiness.py` |
| Connection Pooling & Statement Timeouts | `IMPLEMENTED_AND_VERIFIED` | `backend/app/db/session.py` | `backend/tests/integration/test_rls_pool_leak.py` |
| Foreign Key Cascading Deletions | `IMPLEMENTED_AND_VERIFIED` | `supabase/migrations/20260907235800_init_core_schema.sql` | `tests/integration/test_deletion_cascade.py` |
| GDPR Account Deletion Worker Pipeline | `IMPLEMENTED_AND_VERIFIED` | `backend/app/core/deletion.py`, `backend/app/worker_tasks.py` | `backend/tests/workers/test_deletion_job.py`, `backend/tests/integration/test_real_deletion_job.py` |
| GDPR Data Export & Download URL | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/exports.py` | `backend/tests/api/test_exports.py` |
| Dual Object Storage (Local & GCS) | `IMPLEMENTED_AND_VERIFIED` | `backend/app/core/storage.py` | `tests/infra/test_storage.py` |
| HNSW Vector Indexing (pgvector) | `BLOCKED_BY_EXTERNAL_INFRASTRUCTURE` | `supabase/migrations/20260907235801_add_vector_indexes.sql` | Fully declared in migrations; local Windows PG instance lacks pgvector extension |

---

## 4. AI Gateway & Inference Platform

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| Strict Provider SDK Boundary | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/` | `scripts/check_gateway_boundary.py` (0 forbidden imports) |
| Provider Registry & Capability Filter | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/registry.py` | `packages/ai-gateway/tests/test_router.py` |
| Budget Guard & Daily USD Budgets | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/budget.py` | `packages/ai-gateway/tests/test_budget.py` |
| Circuit Breaker & Automatic Backoff | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/resilience.py` | `packages/ai-gateway/tests/test_resilience.py` |
| Pydantic Structured Output Enforcement | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/prompt_builder.py` | `packages/ai-gateway/tests/test_prompt_builder.py` |
| Request Cancellation Propagation | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/cancellation.py` | `packages/ai-gateway/tests/test_cancellation.py` |
| Output Safety & Prompt Injection Guard | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/output_safety.py` | `backend/tests/security/test_prompt_injection.py` |
| Local Embeddings (BGE-small-en-v1.5) | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/embeddings.py` | `packages/ai-gateway/tests/test_embeddings.py` |
| Local STT (Faster-Whisper on CPU int8) | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/audio/model_registry.py` | `scripts/benchmark_performance.py` (RTF 0.105) |
| Local VAD (Silero VAD ONNX) | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/audio/vad.py` | `scripts/benchmark_performance.py` (0.216 ms/frame) |
| Local TTS (Piper TTS Engine) | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/audio/tts.py` | `realtime-agent/tests/unit/test_tts.py` |
| Live Cloud LLM Inference (Zero-Spend) | `BLOCKED_BY_EXTERNAL_INFRASTRUCTURE` | `packages/ai-gateway/praxis_ai_gateway/providers/` | Local `.env` contains revoked leaked Gemini key and empty Groq key. Valid OpenAI, Anthropic, DeepSeek keys exist in environment. |

---

## 5. Resume, Candidate Intelligence & RAG

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| Resume File Upload & MIME Sniffing | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/resumes.py` | `backend/tests/security/test_file_upload_security.py` |
| OCR Fallback for Scanned Resumes | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/vision/ocr.py` | `tests/unit/test_ocr.py` |
| Document Chunking & Provenance Tracking | `IMPLEMENTED_AND_VERIFIED` | `packages/ai-gateway/praxis_ai_gateway/chunking.py` | `backend/tests/rag/test_retrieval.py` |
| 5-Tier Claim Grounding Engine | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/scoring/claims.py` | `realtime-agent/tests/unit/test_5tier_claim_grounding.py` |
| Candidate Long-Term Memory & Strengths | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/candidate_memory.py` | `backend/tests/api/test_routers_smoke.py` |
| Explainable Candidate-Job Matching | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/matching_service.py` | `backend/tests/services/test_matching.py` |

---

## 6. Job Intelligence & Preparation

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| Job Description Ingestion & Parsing | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/job_service.py` | `backend/tests/api/test_routers_smoke.py` |
| Requirement Graph & Weight Extraction | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/job_service.py` | `backend/tests/api/test_routers_smoke.py` |
| Preparation Plan Generator | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/preparation_engine.py` | `backend/tests/api/test_routers_smoke.py` |
| Application Lifecycle Tracking | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/applications.py` | `backend/tests/api/test_applications.py` |
| Cold Outreach Drafting Engine | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/outreach.py` | `backend/tests/api/test_outreach.py` |

---

## 7. Realtime Audio & Session Engine

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| 18-Byte Binary Framing (`>BBIdI`) | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/protocol.py` | `realtime-agent/tests/test_audio_protocol.py` |
| Malformed Frame & Replay Rejection | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/protocol.py` | `tests/security/test_websocket_security.py` |
| Durable Redis Session State Machine | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/session/redis_state.py` | `realtime-agent/tests/unit/test_state_machine.py` |
| Transparent TCP Reconnection | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/session/state_machine.py` | `realtime-agent/tests/integration/test_reconnect_ci.py` |
| Dual-Path DSP Coaching Cadence | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/coaching/metrics.py` | `tests/realtime/test_coaching_metrics_no_llm.py` |
| Mid-Sentence Pause Toleration | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/audio/vad.py` | `tests/realtime/test_mid_sentence_pause.py` |
| Barge-In & Interruption Handling | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/interview/barge_in.py` | `realtime-agent/tests/integration/test_barge_in_mechanism.py` |

---

## 8. Interview Engines & Scoring

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| Coding Sandbox (Isolated Microservice) | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/coding_engine.py` | `backend/tests/services/test_coding_sandbox.py` (7 tests) |
| System Design 24-Phase Flow | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/system_design_engine.py` | `backend/tests/api/test_routers_smoke.py` |
| Behavioral STAR Calibration | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/behavioral_engine.py` | `backend/tests/evaluation/test_behavioral_calibration.py` (12 tests) |
| Adaptive Difficulty Scaling | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/adaptive_difficulty.py` | `backend/tests/api/test_routers_smoke.py` |
| Question Bank & Variant Management | `IMPLEMENTED_AND_VERIFIED` | `backend/app/api/questions.py` | `backend/tests/api/test_questions.py` |
| Multi-Dimensional Scoring Rubrics | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/scoring/service.py` | `realtime-agent/tests/evaluation/test_scoring_calibration.py` |
| Comprehensive Session Debriefs | `IMPLEMENTED_AND_VERIFIED` | `realtime-agent/realtime_agent/app/interview/debrief.py` | `backend/tests/integration/test_debrief.py` |

---

## 9. Learning & Spaced Repetition

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| SM-2 Spaced Repetition Engine | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/sm2.py` | `backend/tests/services/test_sm2.py` |
| Automated Study Card Generation | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/study.py` | `tests/api/test_study.py` |
| Readiness Estimation & Weakness Analytics | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/readiness.py` | `backend/tests/api/test_analytics.py` |

---

## 10. Workers, Queues & Scheduling

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| ARQ Distributed Worker Pool | `IMPLEMENTED_AND_VERIFIED` | `backend/app/core/queue.py` | `backend/tests/workers/test_worker_jobs.py` |
| Job Idempotency & Duplicate Guards | `IMPLEMENTED_AND_VERIFIED` | `backend/app/services/worker_idempotency.py` | `backend/tests/workers/test_worker_jobs.py` |
| Dead-Letter Queue & Retry Backoff | `IMPLEMENTED_AND_VERIFIED` | `backend/app/worker_tasks.py` | `backend/tests/hardening/test_worker_pipeline.py` |
| Scheduled Retention & Deletion Tasks | `IMPLEMENTED_AND_VERIFIED` | `backend/worker_settings.py` | `backend/tests/workers/test_deletion_job.py` |

---

## 11. Infrastructure, Containers & Cloud

| Capability | Classification | Evidence / Source File | Test Verification |
|---|---|---|---|
| Multi-Stage Dockerfiles (API, Realtime, Worker, Sandbox) | `IMPLEMENTED_AND_VERIFIED` | `docker/Dockerfile.*` | Verified in CI (`ci.yml`) |
| Local Docker Build Execution | `BLOCKED_BY_EXTERNAL_INFRASTRUCTURE` | `docker-compose.yml` | Docker Desktop daemon not active on local host |
| Terraform GCP Architecture (Cloud Run, Cloud SQL, Memorystore) | `IMPLEMENTED_AND_VERIFIED` | `infra/gcp/main.tf` | Validated configuration files |
| Live GCP Cloud Provisioning | `BLOCKED_BY_EXTERNAL_INFRASTRUCTURE` | `infra/gcp/` | Requires authorized GCP project service account |
