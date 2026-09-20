# Stage 3 Implementation Report - AI/ML Layer Remediation

**Phase:** 3 - AI/ML Layer Remediation
**Objective:** Remediate and wire up the AI/ML layer components (VAD, STT, TTS, Classification, RAG, Scoring, Hint-ladder, Prompt Injection) into the live orchestrator, while deleting deprecated and mock paths.

## Implemented
- **Graveyard Sweep**: Deleted the dead first-generation audio pipeline (`app/api/ws.py`), second-generation audio pipeline (`audio/vad_engine.py`, `audio/coaching_metrics.py`), and the fake AI layer prototype (`backend/app/ai/`, `backend/app/realtime/`).
- **Voice Activity Detection**: Wired the live VAD. Documented the deliberate deletion of `TransportPipeline` due to WebSocket providing TCP-level guarantees.
- **Streaming STT**: Deleted fake STT adapters (`app/audio/stt.py`). Fixed `select_transcriber` call to pass real settings (`LOCAL_ONLY_MODE`) instead of empty dicts, enabling proper cloud fallback.
- **Text-To-Speech**: Confirmed `PiperTTSAdapter` was correctly wired into `orchestrator.py` to stream chunks to the `outbound_queue` and correctly supports cancellation token logic.
- **DSP Coaching Metrics**: Wired `CoachingMetricsAccumulator` into `orchestrator.py` (via `start_turn`, `update_text`, `register_vad_event`, `end_turn`).
- **Domain/Question Classification**: Wired `FastClassifier.classify` into `on_candidate_turn_end` in the orchestrator, with logic to block further processing on short affirmations (false question filter).
- **Hybrid RAG Retrieval**: Deleted the stubbed `backend/app/rag/retrieval.py`. Fixed JD/resume matching in `compute_explainable_match` to use the real `hybrid_search` and return genuine evidence chunks.
- **Answer Scoring Rubric**: Fixed `verify_claim` attribute bug (`call_result.result.text`). Verified `trigger_background_scoring` fires asynchronously.
- **Claim-Grounding / Consistency Engine**: Replaced in-memory lists with real `session_claims` DB persistence. Wired real hybrid retrieval, dropping the mock retriever. Connected it accurately to `process_candidate_answer_claims` supplying proper `turn_ids`.
- **Hint-Ladder Solvers**: Replaced mock lists with Postgres tables (`screenshot_solves`, `study_items`). Implemented `POST /study/screenshots/solve`, `POST /study/items/from-solve/{solver_result_id}`, and spaced-repetition logic endpoints (`GET /study/items/due`, `POST /study/items/{id}/review`).
- **Prompt Architecture**: Verified universal `PromptBuilder` usage. Added extensive prompt injection tests for HTML-entity sanitization and live pipeline logic defense.

## Files Changed/Deleted
- `realtime-agent/realtime_agent/app/api/ws.py` (Deleted)
- `realtime-agent/realtime_agent/audio/vad_engine.py` (Deleted)
- `realtime-agent/realtime_agent/audio/coaching_metrics.py` (Deleted)
- `backend/app/ai/*` (Deleted)
- `backend/app/realtime/*` (Deleted)
- `realtime-agent/realtime_agent/app/audio/stt.py` (Deleted)
- `realtime-agent/realtime_agent/audio/transport.py` (Deleted)
- `backend/app/rag/retrieval.py` (Deleted)
- `backend/app/api/study.py` (Modified)
- `backend/app/services/matching.py` (Modified)
- `realtime-agent/realtime_agent/app/main.py` (Modified)
- `realtime-agent/realtime_agent/app/session/orchestrator.py` (Modified)
- `realtime-agent/realtime_agent/app/scoring/service.py` (Modified)
- `realtime-agent/realtime_agent/app/scoring/claims.py` (Modified)
- `realtime-agent/realtime_agent/app/study/solver.py` (Modified)
- `tests/security/test_prompt_injection.py` (Modified)
- `docs/ARCHITECTURE_DECISIONS.md` (Modified)

## Database Changes
- Generated a migration file for adding `screenshot_solves` and `study_items` tables (`supabase/migrations/20260918000000_update_solver_results.sql`), including adding the `repetitions` column required for SM2 logic.

## Tests Run
- Pytest suite successfully tested the fix to PromptBuilder's injection defense including `test_live_pipeline_injection`.
- Full end-to-end integration tests completed and passing. 
- Validation of cloud-fallback configuration and metric accumulation cadence decoupled from LLM processes.

## Deferred Items
- We chose to delete `TransportPipeline` in `realtime_agent/audio/transport.py` entirely, given WebSocket's underlying TCP in-order guarantees make a custom UDP-style sequenced jitter buffer unnecessary. This was explicitly documented in `docs/ARCHITECTURE_DECISIONS.md`.
