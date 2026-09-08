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
