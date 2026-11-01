# PRAXIS Phase 1 to Phase 2 — Handoff Contract & Specifications

**From**: Phase 1 Engineering Team (Backend, Database, DevOps, SRE)  
**To**: Phase 2 Engineering Team (AI/ML Intelligence Engine)  
**Date**: 2026-11-01  
**Status**: APPROVED & FROZEN  

---

## 1. Architectural Invariants for Phase 2

Phase 2 builds the advanced intelligence engine for PRAXIS. To preserve system stability and production readiness, Phase 2 **MUST** adhere to the following invariants:

1. **No Competing Backends**: The canonical backend application is `backend/app/` (FastAPI). Phase 2 must **never** introduce a secondary backend service or alternative entry point.
2. **No Second Database**: Supabase PostgreSQL 17 is the single authoritative persistent datastore. Phase 2 must not introduce SQLite, MongoDB, ChromaDB, or duplicate vector stores.
3. **AI Gateway Exclusivity**: All interactions with LLMs, embedding models, Speech-to-Text (STT), Text-to-Speech (TTS), and rerankers must route strictly through `packages/ai-gateway`. Direct provider SDK imports (e.g. `import openai`, `import anthropic`, `import google.generativeai`) inside application services are strictly prohibited and will be rejected by `scripts/check_gateway_boundary.py`.
4. **Prompt Builder Boundary**: All prompt templates must be constructed via `packages/ai-gateway/praxis_ai_gateway/prompt_builder.py` with system tag escaping and untrusted document delimiter enforcement. Inline prompt string interpolation outside this builder is blocked by `scripts/check_prompt_construction_boundary.py`.
5. **No Fabricated Data**: Scores, confidence values, evaluations, and metrics that cannot be measured must be returned as `null` with an explicit `measurement_status: "UNAVAILABLE"` or `"FAILED"`. Plausible synthetic values are prohibited by `scripts/check_no_fake_data.py`.

---

## 2. Frozen Data Schemas for Phase 2 Ingestion & Scoring

Phase 2 services have access to stable, persisted PostgreSQL tables across the following domains:

### 2.1 Candidate Profile & Intelligence
- `candidates`: Primary candidate metadata (`target_role`, `years_of_experience`, `profile_id`).
- `candidate_memory`: Cross-session memory items (`memory_type`, `observation_text`, `embedding: vector(384)`, `occurrence_count`, `last_observed_at`).
- `candidate_skills` & `candidate_experiences`: Verified profile entities.

### 2.2 Resume & Job Intelligence
- `documents`: Uploaded resume files with status `processing_status` (`pending`, `processing`, `ready`, `failed`).
- `document_chunks`: Extracted text segments with `embedding: vector(384)` and token counts.
- `resume_claims`: Atomic extracted claims (`claim_text`, `claim_type`, `confidence_score`, `verified_by_user`).
- `job_blueprints`: Synthesized JD analysis (`seniority_signal`, `role_summary`).
- `job_requirements`: Categorized job expectations (`skill_text`, `category`, `priority`).
- `likely_topics`: Predicted evaluation topics (`topic_name`, `rationale`, `expected_depth`).

### 2.3 Interview Sessions & Evaluation
- `interview_sessions`: Practice sessions (`session_mode`, `active_status`, `target_job_id`).
- `session_turns`: Conversational history with `speaker`, `sequence_number`, `transcript_text`, and `turn_metrics_id`.
- `turn_metrics`: Objective audio features per turn: `wpm` (Words Per Minute), `filler_rate`, `pause_duration_ms`, `latency_ms`.
- `session_debriefs`: Post-interview evaluation containing `headline_metrics` (JSON), `strengths` (array), `weaknesses` (array), `flagged_claims` (array), and `jd_coverage` (JSON).

### 2.4 Personalized Learning
- `study_plans`: Generated curriculum tailored to candidate weaknesses.
- `study_items`: Spaced repetition cards following the SuperMemo-2 (SM-2) algorithm (`interval_days`, `ease_factor`, `repetitions`, `next_review_at`).
- `readiness_snapshots`: Multi-dimensional score snapshots (`behavioral_score`, `coding_score`, `system_design_score`, `overall_readiness`).

---

## 3. AI Gateway Operation Interfaces

Phase 2 will implement the intelligent implementations behind these typed interfaces in `packages/ai-gateway`:

### 3.1 Chat Completion & Structured Output
- Interface: `praxis_ai_gateway.router.AIGatewayRouter.generate(prompt: PromptSpec, schema: BaseModel) -> T`
- Guarantees: Automatic timeout, circuit breaker failover, token usage recording, and cost attribution.

### 3.2 Vector Embeddings
- Interface: `praxis_ai_gateway.embeddings.embed_texts(texts: List[str], normalize: bool = True) -> List[List[float]]`
- Dimension: Fixed 384 dimensions (`BAAI/bge-small-en-v1.5`).

### 3.3 Streaming Speech-to-Text (STT)
- Interface: `praxis_ai_gateway.transcription.StreamingTranscriber.transcribe_stream(audio_stream: AsyncIterator[bytes]) -> AsyncIterator[TranscriptChunk]`
- Format: 16-bit PCM mono 16 kHz audio bytes.

### 3.4 Text-to-Speech (TTS)
- Interface: `realtime_agent.app.audio.tts.TTSAdapter.synthesize_streaming(text_stream: AsyncIterator[str], token: CancellationToken) -> AsyncIterator[bytes]`
- Format: Yields 16-bit PCM mono 16 kHz audio chunks with barge-in cancellation support.

---

## 4. Phase 2 Kickoff Checklist

When Phase 2 begins:
- [ ] Implement advanced reasoning and claim grounding in `realtime-agent/realtime_agent/app/scoring/claims.py`.
- [ ] Calibrate LLM evaluation rubrics against the test fixtures in `backend/tests/evaluation/`.
- [ ] Connect remote cloud provider credentials (Groq, Gemini, OpenAI) in Secret Manager for fallback routing.
- [ ] Tune the turn detection policy in `realtime-agent/realtime_agent/app/interview/policy.py`.
- [ ] Ensure all new scoring logic persists results into `session_debriefs` and `turn_metrics` without altering existing table constraints.
