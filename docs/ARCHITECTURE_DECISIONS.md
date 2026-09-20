# Architecture Decisions

## ADR-002: Job Queue - arq over Celery

**Context & Problem:**
Background work (document parsing, embedding generation, debrief generation, cleanup jobs) needs a durable queue. Stage 2 API logic will be built entirely on asyncio-native FastAPI.

**Decision:**
We will use **arq** instead of Celery.

**Reasoning:**
- **Async-native:** Celery's mainstream worker model is synchronous/prefork by default. Layering async work under it often requires event-loop-per-task or gevent-style workarounds that fight the rest of our stack. `arq` is built directly on asyncio, matching our codebase's idioms (`async def process_resume(...)`).
- **Dependency Footprint:** `arq` requires no separate broker beyond the Redis instance already provisioned for caching and session state in Phase 1.8.

**Tradeoffs:**
- `arq` has a smaller ecosystem and fewer built-in features than Celery.
- There is no built-in equivalent to Flower for a comprehensive dashboard.
- It offers simpler retry/backoff primitives.
For our project's scale, an async-native paradigm with zero operational overhead for an extra broker is an acceptable and favorable trade, not a compromise being apologized for.

## ADR-001: Deliberate Scoping of PRAXIS as a Practice Tool

**Date:** 2026-09-07

### Context
We are building a realtime AI interview system. There are two potential products we could build with a realtime audio pipeline and a candidate knowledge graph: an answer-feeding copilot for use during real interviews, or a realtime AI interview coach for practice sessions (PRAXIS).

### Decision
We have explicitly chosen to build PRAXIS, the practice and coaching tool, and have scoped away live-interview assistance. 

### Rationale
The practice tool is a strictly larger and more complex engineering problem. A one-way "audio in -> answer out" pipeline (copilot) never has to solve:
- Turn-taking
- Barge-in cancellation
- Speaker-conditioned VAD (Voice Activity Detection)
- Realtime prosodic feature extraction

These complex features are the exact technical challenges that demonstrate strong engineering judgment and capability. Furthermore, building a practice tool is ethically sound, can be openly demoed to judges or interviewers, and serves as a strong portfolio piece, unlike a copilot which carries ethical DQ risks and cannot be safely demonstrated or discussed in interviews.

### Consequences
- We will implement a bidirectional audio pipeline.
- We will prioritize low-latency turn-taking and barge-in handling.
- The application will be a standard OS window with no hidden capture-evasion or stealth modes.

## ADR-002: Spaced Repetition (Study Loop)
**Date:** 2026-09-07
We elected to use the **SuperMemo-2 (SM-2)** algorithm for our study review scheduling.
- **Why**: It is a mathematically proven, robust algorithm that avoids the complexity and unpredictability of LLM-based spaced repetition or bespoke neural networks.
- **How**: It computes an explicit `ease_factor` and `interval_days` based on a deterministic `0-5` quality rating from the candidate.

## ADR-003: Defense in Depth — RLS is the Backstop, Not the Primary Access Control
**Context:** Supabase's Row Level Security (RLS) policies are highly effective at scoping data access when the database connection is established with an authenticated user's JWT. However, application-level backend logic often needs to connect using the service_role key to execute complex background tasks or manage cross-user aggregations. The service_role explicitly bypasses all RLS policies.
**Decision:** Every query built in the FastAPI routers MUST explicitly filter by the authenticated candidate_id at the application query level (e.g., .where(model.candidate_id == current_user.id)). We will never omit a WHERE clause under the assumption that "RLS will filter out the rest". 
**Consequences:** 
1. **Prevents catastrophic data leaks:** If an endpoint is inadvertently executed with elevated privileges or a service token, the explicit query boundaries ensure data from other users is not leaked.
2. **Clarifies intent:** Reading the router logic makes the data access boundaries immediately obvious to other developers without having to jump into SQL migration files.

## ADR-004: Separate Realtime Agent Process

**Context & Problem:**
The system must handle latency-sensitive active audio sessions (requiring <2s turnaround times) simultaneously with heavy background operations like PDF resume parsing, embedding computation, or complex analytics aggregations. Python's asyncio event loop is single-threaded for CPU-bound work.

**Decision:**
The realtime WebSocket logic (`realtime-agent`) will run as a genuinely separate OS process (on its own port/ASGI instance) from the core REST API (`backend`).

**Reasoning:**
Even if heavily structured using `async def`, a CPU-bound segment (e.g., synchronous tokenization, JSON parsing, or heavy ORM instantiation) can introduce scheduling delays or GIL contention that block the event loop. If a resume-parsing route handler shares an event loop with an active audio WebSocket, the WebSocket's turn-taking and audio acknowledgment frames will stall, directly violating our <2s realtime latency budget. Running them in genuinely separate OS processes guarantees strict OS-level scheduling isolation that "just don't do CPU-heavy things in this route handler" discipline cannot reliably guarantee as the codebase grows.

**Consequences:**
- The Realtime Agent handles ONLY WebSockets and lightweight health checks.
- The Core API handles ALL heavy REST/CRUD and orchestrates `arq` workers.
- The two processes share the Redis pool (for rate limiting, JWKS caching, and circuit breaker state) and PostgreSQL, but never share an event loop.

## ADR-005: Local-First AI/ML Stack Selection

**Date:** 2026-09-08

**Context:** 
We require highly responsive local inference models for the PRAXIS realtime audio pipeline and background processing. These models must be performant enough to meet the 2-second turnaround time budget for a complete STT -> Planning -> TTS loop, even on a CPU-only developer machine if necessary.

**Decision:**
We explicitly selected the following AI/ML primitives based on strict performance and architecture constraints:

1. **faster-whisper over openai-whisper (STT):**
   The `CTranslate2` backend gives materially faster inference, especially on CPU. This is not a marginal optimization; it is the difference between a usable and unusable local STT path. Standard `whisper` is too slow for realtime interactions unless heavily accelerated by top-tier GPUs, which breaks the local-first ethos.

2. **Silero VAD over WebRTC VAD (VAD):**
   Silero is substantially more accurate at distinguishing speech from background noise or silence at a similar computational cost. This matters directly because a false-positive VAD trigger would incorrectly fire Stage 2's barge-in controller, rudely interrupting the interviewer or assuming the user has spoken when they haven't. ONNX execution keeps it under ~2MB and extremely fast.

3. **Piper over heavy neural TTS (TTS):**
   Piper trades a small amount of voice naturalness for genuinely real-time synthesis speed and an incredibly small memory footprint. For an interviewer persona that needs to start speaking quickly to emulate natural conversational flow, this is the correct trade-off compared to a heavier, higher-quality narrator model which could introduce seconds of latency.

4. **BAAI/bge-small-en-v1.5 over larger embedding models (Embeddings):**
   This model outputs 384 dimensions, keeping the HNSW index from Stage 1 fast and small at portfolio data volumes. Retrieval quality at this scale is dominated by chunking and retrieval-strategy quality more than by marginal embedding-model quality gains. Fixing it at 384 dimensions is a considered trade-off for speed and minimal indexing overhead, rather than an unexamined default.

5. **Ollama qwen2.5 (Local LLMs):**
   For local classification and reasoning, the `qwen2.5` model family provides a strong balance of context length, reasoning capability, and footprint. `qwen2.5:3b` runs comfortably on ~4GB RAM, providing a fallback fast-classify endpoint, while `qwen2.5:14b` offers high reasoning quality where hardware (12GB+ VRAM or 16GB+ System RAM) permits.

## ADR-006: Prompt/Model Change Regression Policy

**Date:** 2026-09-08
**Status:** Accepted

### Context
The master spec (Part 196) requires that prompt and model changes be treated as measurable engineering changes rather than subjective feelings. Modifying prompts/ or altering model routes in config/models.yaml risks breaking established pipeline boundaries. We need an operationalized regression gate.

### Decision
Any change to a file under prompts/ or an alias mapping in config/models.yaml MUST be followed by executing the evaluation harness:
uv run scripts/run_evaluation.py

Before merging the Pull Request, the generated report (docs/evaluation_reports/<date>_baseline.md) must be reviewed against the prior baseline.

**Concrete Regression Thresholds:**
1. **Classification Accuracy:** Must not drop by more than **5 percentage points**.
# Architecture Decisions

## ADR-002: Job Queue - arq over Celery

**Context & Problem:**
Background work (document parsing, embedding generation, debrief generation, cleanup jobs) needs a durable queue. Stage 2 API logic will be built entirely on asyncio-native FastAPI.

**Decision:**
We will use **arq** instead of Celery.

**Reasoning:**
- **Async-native:** Celery's mainstream worker model is synchronous/prefork by default. Layering async work under it often requires event-loop-per-task or gevent-style workarounds that fight the rest of our stack. `arq` is built directly on asyncio, matching our codebase's idioms (`async def process_resume(...)`).
- **Dependency Footprint:** `arq` requires no separate broker beyond the Redis instance already provisioned for caching and session state in Phase 1.8.

**Tradeoffs:**
- `arq` has a smaller ecosystem and fewer built-in features than Celery.
- There is no built-in equivalent to Flower for a comprehensive dashboard.
- It offers simpler retry/backoff primitives.
For our project's scale, an async-native paradigm with zero operational overhead for an extra broker is an acceptable and favorable trade, not a compromise being apologized for.

## ADR-001: Deliberate Scoping of PRAXIS as a Practice Tool

**Date:** 2026-09-07

### Context
We are building a realtime AI interview system. There are two potential products we could build with a realtime audio pipeline and a candidate knowledge graph: an answer-feeding copilot for use during real interviews, or a realtime AI interview coach for practice sessions (PRAXIS).

### Decision
We have explicitly chosen to build PRAXIS, the practice and coaching tool, and have scoped away live-interview assistance. 

### Rationale
The practice tool is a strictly larger and more complex engineering problem. A one-way "audio in -> answer out" pipeline (copilot) never has to solve:
- Turn-taking
- Barge-in cancellation
- Speaker-conditioned VAD (Voice Activity Detection)
- Realtime prosodic feature extraction

These complex features are the exact technical challenges that demonstrate strong engineering judgment and capability. Furthermore, building a practice tool is ethically sound, can be openly demoed to judges or interviewers, and serves as a strong portfolio piece, unlike a copilot which carries ethical DQ risks and cannot be safely demonstrated or discussed in interviews.

### Consequences
- We will implement a bidirectional audio pipeline.
- We will prioritize low-latency turn-taking and barge-in handling.
- The application will be a standard OS window with no hidden capture-evasion or stealth modes.

## ADR-002: Spaced Repetition (Study Loop)
**Date:** 2026-09-07
We elected to use the **SuperMemo-2 (SM-2)** algorithm for our study review scheduling.
- **Why**: It is a mathematically proven, robust algorithm that avoids the complexity and unpredictability of LLM-based spaced repetition or bespoke neural networks.
- **How**: It computes an explicit `ease_factor` and `interval_days` based on a deterministic `0-5` quality rating from the candidate.

## ADR-003: Defense in Depth — RLS is the Backstop, Not the Primary Access Control
**Context:** Supabase's Row Level Security (RLS) policies are highly effective at scoping data access when the database connection is established with an authenticated user's JWT. However, application-level backend logic often needs to connect using the service_role key to execute complex background tasks or manage cross-user aggregations. The service_role explicitly bypasses all RLS policies.
**Decision:** Every query built in the FastAPI routers MUST explicitly filter by the authenticated candidate_id at the application query level (e.g., .where(model.candidate_id == current_user.id)). We will never omit a WHERE clause under the assumption that "RLS will filter out the rest". 
**Consequences:** 
1. **Prevents catastrophic data leaks:** If an endpoint is inadvertently executed with elevated privileges or a service token, the explicit query boundaries ensure data from other users is not leaked.
2. **Clarifies intent:** Reading the router logic makes the data access boundaries immediately obvious to other developers without having to jump into SQL migration files.

## ADR-004: Separate Realtime Agent Process

**Context & Problem:**
The system must handle latency-sensitive active audio sessions (requiring <2s turnaround times) simultaneously with heavy background operations like PDF resume parsing, embedding computation, or complex analytics aggregations. Python's asyncio event loop is single-threaded for CPU-bound work.

**Decision:**
The realtime WebSocket logic (`realtime-agent`) will run as a genuinely separate OS process (on its own port/ASGI instance) from the core REST API (`backend`).

**Reasoning:**
Even if heavily structured using `async def`, a CPU-bound segment (e.g., synchronous tokenization, JSON parsing, or heavy ORM instantiation) can introduce scheduling delays or GIL contention that block the event loop. If a resume-parsing route handler shares an event loop with an active audio WebSocket, the WebSocket's turn-taking and audio acknowledgment frames will stall, directly violating our <2s realtime latency budget. Running them in genuinely separate OS processes guarantees strict OS-level scheduling isolation that "just don't do CPU-heavy things in this route handler" discipline cannot reliably guarantee as the codebase grows.

**Consequences:**
- The Realtime Agent handles ONLY WebSockets and lightweight health checks.
- The Core API handles ALL heavy REST/CRUD and orchestrates `arq` workers.
- The two processes share the Redis pool (for rate limiting, JWKS caching, and circuit breaker state) and PostgreSQL, but never share an event loop.

## ADR-005: Local-First AI/ML Stack Selection

**Date:** 2026-09-08

**Context:** 
We require highly responsive local inference models for the PRAXIS realtime audio pipeline and background processing. These models must be performant enough to meet the 2-second turnaround time budget for a complete STT -> Planning -> TTS loop, even on a CPU-only developer machine if necessary.

**Decision:**
We explicitly selected the following AI/ML primitives based on strict performance and architecture constraints:

1. **faster-whisper over openai-whisper (STT):**
   The `CTranslate2` backend gives materially faster inference, especially on CPU. This is not a marginal optimization; it is the difference between a usable and unusable local STT path. Standard `whisper` is too slow for realtime interactions unless heavily accelerated by top-tier GPUs, which breaks the local-first ethos.

2. **Silero VAD over WebRTC VAD (VAD):**
   Silero is substantially more accurate at distinguishing speech from background noise or silence at a similar computational cost. This matters directly because a false-positive VAD trigger would incorrectly fire Stage 2's barge-in controller, rudely interrupting the interviewer or assuming the user has spoken when they haven't. ONNX execution keeps it under ~2MB and extremely fast.

3. **Piper over heavy neural TTS (TTS):**
   Piper trades a small amount of voice naturalness for genuinely real-time synthesis speed and an incredibly small memory footprint. For an interviewer persona that needs to start speaking quickly to emulate natural conversational flow, this is the correct trade-off compared to a heavier, higher-quality narrator model which could introduce seconds of latency.

4. **BAAI/bge-small-en-v1.5 over larger embedding models (Embeddings):**
   This model outputs 384 dimensions, keeping the HNSW index from Stage 1 fast and small at portfolio data volumes. Retrieval quality at this scale is dominated by chunking and retrieval-strategy quality more than by marginal embedding-model quality gains. Fixing it at 384 dimensions is a considered trade-off for speed and minimal indexing overhead, rather than an unexamined default.

5. **Ollama qwen2.5 (Local LLMs):**
   For local classification and reasoning, the `qwen2.5` model family provides a strong balance of context length, reasoning capability, and footprint. `qwen2.5:3b` runs comfortably on ~4GB RAM, providing a fallback fast-classify endpoint, while `qwen2.5:14b` offers high reasoning quality where hardware (12GB+ VRAM or 16GB+ System RAM) permits.

## ADR-006: Prompt/Model Change Regression Policy

**Date:** 2026-09-08
**Status:** Accepted

### Context
The master spec (Part 196) requires that prompt and model changes be treated as measurable engineering changes rather than subjective feelings. Modifying prompts/ or altering model routes in config/models.yaml risks breaking established pipeline boundaries. We need an operationalized regression gate.

### Decision
Any change to a file under prompts/ or an alias mapping in config/models.yaml MUST be followed by executing the evaluation harness:
uv run scripts/run_evaluation.py

Before merging the Pull Request, the generated report (docs/evaluation_reports/<date>_baseline.md) must be reviewed against the prior baseline.

**Concrete Regression Thresholds:**
1. **Classification Accuracy:** Must not drop by more than **5 percentage points**.
2. **Grounding Precision:** Must not drop by more than **5 percentage points**.
3. **Latency:** p95 end-to-end latency must not increase by more than **20%**.

### Consequences
If a metric regresses beyond these thresholds, the author must explicitly justify the regression in the PR description or revert the change. This transforms prompt engineering into a tracked, defensible engineering discipline.

## ADR-007: Deletion of Custom UDP Transport (transport.py)
**Date:** 2026-09-18
We deleted the custom jitter buffer and sequence reordering logic in `transport.py`. Audio is ingested via WebSockets (which provide TCP-level in-order delivery guarantees) or WebRTC (which provides its own robust jitter buffering and ordering). Thus, a custom application-layer jitter buffer in Python is redundant, introduces unnecessary complexity, and increases latency.

## ADR-008: Next.js App Directory Precedence
**Date:** 2026-09-19
**Context:** Next.js uses `src/app/` in precedence over a root `app/` directory. The repository had competing directories resulting in silent overrides.
**Decision:** All production code (Dashboard, Review, Study, Auth) has been migrated definitively to `src/app/`, using the `(dashboard)` route group layout pattern. The root `app/` directory was structurally discarded.

## ADR-009: Consolidated Auth Flow
**Date:** 2026-09-19
**Context:** Competing split route structures existed for authentication (`/auth` vs `(auth)/login` + `(auth)/signup`).
**Decision:** We maintained `/auth` as the single point of entry because it encapsulates the login vs signup state toggle effectively and provides a clean mock fallback. We deleted the empty `(auth)` route group completely. The desktop application will inherit and read the auth token seamlessly via secure storage (`safeStorage`) passing it via WebSocket and API headers rather than recreating an entirely new auth modal.

## ADR-010: Screen Capture Strategy
**Date:** 2026-09-19
**Context:** Two competing capture flows existed (Native Electron Global Shortcut vs Browser getDisplayMedia).
**Decision:** We consolidated fully to the Native Electron Global Shortcut (`CommandOrControl+Shift+S`) bound in the Main process via `desktopCapturer`. The captured PNG buffer is piped back via IPC (`capture-ready`) to the Study Workbench. This honors the strict requirement of an explicit single-keypress user interaction.

## ADR-011: Graveyard Sweep and Legacy Gateway
**Date:** 2026-09-19
**Context:** A legacy gateway implementation was present but fundamentally broken and not CI-enforced.
**Decision:** We strictly deleted the legacy tree under `packages/ai-gateway/` and standardized exclusively on `praxis_ai_gateway/`.

## ADR-012: Debrief Service Dual Paths
**Date:** 2026-09-19
**Context:** Both `backend/app/services/debrief.py` and `realtime-agent/app/interview/debrief.py` existed to generate post-session debriefs, leading to a risk of inconsistent or fabricated implementations.
**Decision:** We are retaining both implementations with a strictly defined, explicit relationship. The realtime-agent's copy is what runs AUTOMATICALLY at the end of a live session. The backend copy exists to regenerate a debrief ON DEMAND from already-persisted session data (`session_turns`, `turn_scores`, `turn_metrics`). Because the backend copy operates post-hoc, it explicitly queries REAL Postgres tables for that data rather than relying on an in-memory `db_stub`. Neither implementation is permitted to use fake template-fill blocks on failure; they must return a minimal, clearly-labeled incomplete result on model failure.

## ADR-013: wait vs wait_cancelled Naming
**Date:** 2026-09-19
**Context:** A discrepancy existed where `resilience.py` expected `.wait()` but `CancellationToken` provided `.wait_cancelled()`.
**Decision:** Standardized on `wait_cancelled()` universally to accurately reflect the semantic behavior of yielding until a cancellation occurs.

## ADR-014: Turn Detection Module Consolidation
**Date:** 2026-09-19
**Context:** During an audit, we examined the relationship between `interview/turn_detection.py` and `audio/turn_detection.py`. The latter was a legacy file that overlapped in responsibility.
**Decision:** We consolidated heuristics into a single, purpose-built module at `interview/turn_detection.py`. Phase 2.10 will exclusively use this module for detecting turn-completeness. It enforces a strict division of labor: the lower-level VAD system reports silence durations, and `interview/turn_detection.py` combines that raw timing with a high-level semantic LLM completeness check (`fast_classify`). This prevents false interruptions during mid-sentence pauses while discarding the separate, redundant `audio/turn_detection.py` implementation.

## ADR-015: Orphaned Extraction Worker Deletion
**Date:** 2026-09-19
**Context:** An orphaned, fake extraction worker existed outside the CI bounds, while the true resume processing logic lived in `worker_tasks.py`.
**Decision:** We deleted the orphaned worker file. The `backend/app/workers/` directory is intentionally retained as a structural placeholder for the remaining `document_worker.py` and `embedding_worker.py` (and any future worker-adjacent modules), though core resume extraction is strictly delegated to `backend/app/worker_tasks.py`.
## ADR-015: AI/ML Graveyard Sweep
**Date:** 2026-09-20
**Context:** Three generations of audio and AI pipelines coexisted in the codebase, leading to confusion and dead code.
**Decision:** We performed a Graveyard Sweep.
1. Deleted ealtime-agent/realtime_agent/app/api/ws.py\ (dead first-gen pipeline).
2. Deleted ealtime-agent/realtime_agent/audio/vad_engine.py\ and \coaching_metrics.py\ (dead second-gen pipeline).
3. Deleted \ackend/app/ai/\ and \ackend/app/realtime/\ entirely (fake AI prototype layer). \ackend/app/realtime/session.py\ was used only as a design reference and NOT preserved, strictly enforcing the separate-process architecture.

## ADR-016: Frame Transport Deferral
**Date:** 2026-09-20
**Context:** The \TransportPipeline\ module offered frame-level reordering and latency tracking, but the WebSocket ingest path reads raw bytes without sequencing.
**Decision:** We deliberately deferred frame-level reordering and latency tracking, deleting \TransportPipeline\, in favor of relying on WebSockets' guaranteed ordered delivery over TCP to simplify the ingestion pipeline.

## ADR-017: Non-Blocking Background Scoring
**Date:** 2026-09-20
**Context:** The LLM-based answer scoring can take several seconds, which would block the interview state machine and increase latency if awaited during turn transitions.
**Decision:** We run scoring asynchronously. \	rigger_background_scoring()\ uses \syncio.create_task()\ to intentionally fire-and-forget the evaluation task without awaiting it. This guarantees the interview loop (and subsequently the interviewer's next reply generation) never blocks on the scoring process.

## ADR-018: Asynchronous Claim Grounding
**Date:** 2026-09-20
**Context:** Extracting claims, checking consistency, and grounding them against retrieval takes time and shouldn't block the state machine.
**Decision:** We run claim grounding asynchronously. \	rigger_background_scoring()\ acts as a fork point that spawns both the LLM rubric evaluation (ADR-017) and the claim-grounding pipeline (\process_candidate_answer_claims\) in the background, keeping the interview loop fast.
## ADR-003: Desktop App Authentication Strategy
**Date:** 2026-09-20
**Context:** Desktop app needs authentication to sync with web platform.
**Decision:** We will use the secure storage bridge (Phase 4.2) to store a mock-token or Supabase session, allowing the desktop app to manage its own login state securely through IPC.

## ADR-004: Next.js Directory Migration
**Date:** 2026-09-20
**Context:** Two competing app directories existed (app/ and src/app/).
**Decision:** Migrated all real pages from apps/web/app/ into apps/web/src/app/(dashboard) and deleted apps/web/app/. Used a single authentication entry point (/auth).

## ADR-005: Screenshot Capture Path
**Date:** 2026-09-20
**Context:** Two disconnected screenshot paths existed: Electron-native and getDisplayMedia.
**Decision:** We chose the Electron-native path (desktopCapturer via global shortcut) for a single-keypress capture experience.

## ADR-006: Web App Practice Page Removal
**Date:** 2026-09-20
**Context:** The web app had an isolated practice page, but the desktop app is the primary target for live practice.
**Decision:** We deleted apps/web/src/app/practice/page.tsx, keeping live practice exclusive to the desktop app.

## ADR-019: Real-Supabase Migration Parity
**Date:** 2026-09-20
**Context:** The SQL migrations use 'MOCK' and 'local dev only' comments for defining auth primitives and schemas (e.g. auth.uid(), storage schema/tables) that are pre-provided by Supabase.
**Decision:** The migrations use "CREATE OR REPLACE FUNCTION", "CREATE SCHEMA IF NOT EXISTS", and "CREATE TABLE IF NOT EXISTS" for these primitives. This makes the migrations completely safe and idempotent for real-Supabase deployments. In a real Supabase environment, the existing Supabase schemas (auth, storage) will be untouched, and our mock auth.uid() definition uses dynamic current_setting, which avoids colliding with real Supabase internals if used correctly.
**Migration Tool Choice:** When deploying to a real, hosted Supabase project, you must use `scripts/migrate.py` pointed at the real project's connection string via the `DATABASE_URL` environment variable. The hardcoded `postgresql://praxis:dev_password@localhost:5432/praxis` is strictly a local-fallback default.

**First-Time Real-Supabase Setup Checklist:**
1. **Link the Project:** Use the Supabase CLI (`supabase link`) or fetch your real database connection string.
2. **Verify Primitives:** Confirm the real Supabase `auth.uid()` and `authenticated` role exist. The idempotent migrations will not overwrite them.
3. **Set Environment Variable:** Export `DATABASE_URL` with your real connection string (e.g., `export DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres`).
4. **Run Migrations:** Execute `python scripts/migrate.py` to apply all migrations idempotently to the real project.

## ADR-020: Enforcing UI Design Consistency (Dark Theme)
**Date:** 2026-09-20
**Context:** Migrated Next.js dashboard pages (Analytics, Candidates, Study Workbench, Platform Tracker) used inconsistent light-theme styling (bg-white, text-gray-600) compared to the overarching dark, dense aesthetic of the desktop and web shell layout (bg-gray-950).
**Decision:** We programmatically migrated all light-theme utility classes in pps/web/src/app/(dashboard) to their dark-theme equivalents (e.g. bg-gray-900, text-gray-400, border-gray-800) to ensure a cohesive and dense dark aesthetic across the entire application interface.

## ADR-021: Server-Side Screenshot Extraction
**Date:** 2026-09-20
**Context:** When a user captures a screenshot for the hint ladder feature, we had to decide whether to perform local OCR on the client (desktop app) and send the extracted text, or send the raw image to the server for centralized OCR and multimodal processing.
**Decision:** We chose Server-Side Extraction (Option A). The desktop app sends the raw base64 image data to the server (/study/screenshots/solve), and the server orchestrates the OCR extraction (un_local_ocr) alongside classification and deep reasoning.
**Rationale:** Centralizing the OCR extraction pipeline on the server makes vision escalation strictly a server-level decision rather than shipping local heuristic branching rules in the desktop app. It allows us to upgrade extraction quality without asking users to redownload the application.
