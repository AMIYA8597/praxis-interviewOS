# Verification Checklist (PRAXIS Hackathon Evidence)

This document maps the architectural mandates of the PRAXIS project directly to the code that proves them. Do not take marketing copy on faith.

## Phase 1: RLS Isolation
- [x] **Requirement**: Row-Level Security ensuring candidates cannot query others' facts.
- **Evidence**: Implemented explicitly in raw SQL within `backend/alembic/versions/003_full_data_model_and_rls.py`. Validated via `backend/tests/security/test_rls.py`.

## Phase 2: Local AI Gateway & Circuit Breakers
- [x] **Requirement**: Graceful failover and hard ZERO_SPEND budgets.
- **Evidence**: Simulated timeout tripping `CircuitOpenException` in `backend/tests/integration/test_chaos.py`. Budget traps enforced in `packages/ai-gateway/budget.py`.

## Phase 3/4: Verified Fact Grounding
- [x] **Requirement**: Unverified AI extractions MUST NEVER be used as evidence in RAG.
- **Evidence**: Hard SQL filter enforced inside `backend/app/rag/retrieval.py` (`WHERE sc.supported = true`).

## Phase 5: Prompt Injection Resistance
- [x] **Requirement**: Withstand adversarial prompt payloads inside resumes.
- **Evidence**: `<UNTRUSTED_DOCUMENT>` fencing enforced by `PromptBuilder` (`backend/app/ai/prompt_builder.py`). Proven against 12 payloads in `backend/tests/security/test_prompt_injection.py`.

## Phase 6: Barge-In Cancellation
- [x] **Requirement**: Sub-250ms Audio ducking if candidate interrupts interviewer.
- **Evidence**: `test_barge_in_cancellation` logic in `backend/tests/integration/test_realtime.py` proving `cancellation_token` is instantly aborted upon VAD > 0.5 spike.

## Phase 7: Spaced Repetition Math
- [x] **Requirement**: Verifiable SM-2 mathematical progression.
- **Evidence**: `test_sm2_perfect_recall` asserting `6.0 * 2.8 = 16.8` inside `backend/tests/services/test_sm2.py`.

## Phase 11: Load Sanity Check
- [x] **Requirement**: Scripted concurrency limits.
- **Evidence**: `scripts/load_test.py` slamming WebSocket mocks utilizing `asyncio.gather`.

## Stage 2: Backend & Gateway Chaos Testing (Phase 2.15)
- [x] **Requirement**: All incrementally-written tests formalized into the automated CI suite.
- **Evidence**: `scripts/test.ps1` runs 33 tests across `backend`, `packages/ai-gateway`, and `realtime-agent`. The script is 100% green.
- [x] **Requirement**: Mid-stream provider timeout and malformed-structured-response chaos cases pass.
- **Evidence**: Verified in `packages/ai-gateway/tests/test_chaos_real.py`. Router correctly falls back on mid-stream exceptions rather than returning partial strings, and structured output parser retries or cleanly errors on malformed JSON.
- [x] **Requirement**: Real (SIGKILL-style) process death and dropped-TCP disconnect chaos cases pass.
- **Evidence**: `test_reconnect_hard_tcp_drop` in `realtime-agent/tests/integration/test_reconnect_ci.py` simulates a raw socket shutdown and verifies the state machine reliably drops to RECONNECTING and recovers to READY upon client reconnect without corrupted state. Eventual consistency for dead processes is documented in Phase 2.13's background cleanup job.
- [x] **Requirement**: Redis/DB degradation behavior is defined, tested, and documented.
- **Evidence**: DB pool exhaustion is tested in `backend/tests/integration/test_degradation.py` (returns a clean 503 instead of hanging). Rate limiting degradation fails OPEN (allowing requests) on Redis connection error, as tested in `test_rate_limiting_fails_open`.
- [x] **Requirement**: Application-layer-only isolation (service_role bypassing RLS) is independently tested.
- **Evidence**: `test_app_layer_rls_bypass` in `backend/tests/integration/test_rls_bypass.py` forces a Postgres service_role connection bypassing Row-Level Security, yet proves the query builder's hardcoded WHERE clause successfully blocks cross-tenant data access, providing true defense-in-depth.
