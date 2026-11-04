# PRAXIS InterviewOS — Sovereign Backend Independence Specification

**Document Version:** 1.0.0  
**Status:** Certified & Active  
**Target Deployment:** Google Cloud Platform (Cloud Run, Cloud SQL, Memorystore)  
**Consumer Model:** Independent Frontend Platform (Zero framework lock-in; consumes REST `/api/v1` and WebSocket `/ws`)

---

## 1. Architectural Philosophy: The Sovereign Backend

PRAXIS InterviewOS is architected as an autonomous, sovereign backend platform. The core API and Realtime agent encapsulate **100% of the business logic, security policies, data persistence, and AI orchestration**. 

The backend **does not depend on Next.js, Electron, browser state, local storage, or any particular client framework** to execute its functions. Any consumer—whether a web application, mobile client, CLI tool, or automated testing suite—can interact with the platform solely through standard, documented HTTP/REST and WebSocket protocols.

```
       +--------------------------------------------------------+
       |           Independent Frontend Clients                 |
       |  (Web / iOS / Android / Desktop / CLI / Headless)      |
       +-------------------+----------------+-------------------+
                           |                |
                HTTPS REST |                | WSS Binary Frame
                /api/v1/*  |                | /ws/sessions/{id}
                           v                v
       +-------------------+----------------+-------------------+
       |            PRAXIS SOVEREIGN BACKEND PLATFORM           |
       |                                                        |
       |  [Core FastAPI Service]        [Realtime Agent WS]     |
       |  - Auth & JWT Verification     - 18-Byte Binary Frame  |
       |  - Candidate Profile & Memory  - Silero VAD & Whisper  |
       |  - Resume & JD Intelligence    - Dual-Path DSP Coach   |
       |  - Adaptive Difficulty         - Redis State Machine   |
       |  - 24-Phase System Design      - Turn Scoring Engine   |
       |  - Sandboxed Code Execution    - 5-Tier Claim Ground   |
       |  - SM-2 Spaced Repetition      - Piper TTS Generator   |
       |                                                        |
       |  [Background Workers (ARQ)]    [AI Gateway Boundary]   |
       |  - Resume Parsing & Chunking   - Circuit Breakers      |
       |  - Vector Embeddings (BGE)     - Budget Guards         |
       |  - GDPR Account Deletion       - Provider Fallbacks    |
       |  - GDPR Data Archive Export    - Structured Pydantic   |
       +-------------------+----------------+-------------------+
                           |                |
                           v                v
       +-------------------+----------------+-------------------+
       |        Authoritative Persistence & Infrastructure      |
       |  - PostgreSQL 17/18 (70 Business Tables, FORCE RLS)    |
       |  - Redis 7 (Transient State, Token Bucket Rate Limit)  |
       |  - Cloud Storage (Private Resumes & Audio Buffers)     |
       +--------------------------------------------------------+
```

---

## 2. Capabilities Owned Entirely by the Backend

The frontend is strictly a presentation and input capture layer. The backend completely owns:

1. **Authentication & Identity Integration:**
   - Validates JWT tokens against Supabase JWKS public keys.
   - Verifies issuer (`iss`), audience (`aud`), expiration (`exp`), and subject (`sub`).
   - Resolves caller identities without trusting client-supplied candidate IDs.
2. **Authorization & Tenant Isolation:**
   - Enforces object-level ownership checks across all endpoints.
   - Enforces PostgreSQL `ENABLE + FORCE ROW LEVEL SECURITY` across all 70 application tables.
   - Prevents User A from reading, modifying, or inferring User B's records.
3. **Candidate Profiles & Long-Term Memory:**
   - Ingests and normalizes skills, experiences, and verified project accomplishments.
   - Tracks persistent weaknesses, recurring communication mistakes, and topic mastery trajectories over time.
4. **Resume Processing & Evidence Extraction:**
   - Validates MIME signatures and file safety (PDF, DOCX, TXT).
   - Extracts sections, facts, numerical claims, and chunks with exact provenance links.
   - Generates local 384-dimensional dense vector embeddings using `BAAI/bge-small-en-v1.5`.
5. **Job Description Intelligence:**
   - Parses unstructured JD text into structured requirement graphs.
   - Categorizes requirements into essential vs. preferred skills and seniority signals.
   - Computes explainable candidate-to-job match percentages.
6. **Adaptive Interview Policy:**
   - Dynamically selects questions and follow-ups based on candidate evidence, past weak areas, and JD coverage gaps.
   - Adjusts difficulty dynamically (levels 1 through 5) based on real-time scoring.
7. **Realtime Audio & Speech Processing:**
   - Ingests raw PCM16 audio buffers using an 18-byte binary framing protocol (`>BBIdI`).
   - Silero VAD detects speech boundaries locally in under 1 ms per frame.
   - Faster-Whisper transcribes speech locally on CPU in int8 (Realtime Factor: 0.105).
   - Piper TTS generates interviewer audio responses locally.
8. **Dual-Path Coaching Engine:**
   - Low-latency DSP path computes speaking pace (WPM), filler word count, and pause duration on a strict 1-second cadence without waiting for LLM completions.
   - Semantic evaluation path scores responses across relevance, correctness, depth, and clarity.
9. **5-Tier Claim Grounding:**
   - Classifies spoken candidate claims as `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, or `UNCERTAIN` against verified resume facts.
10. **Specialized Technical Engines:**
    - **Coding Execution:** Untrusted code runs exclusively in an isolated, network-disabled sandbox container with CPU and memory limits.
    - **System Design:** Orchestrates a 24-phase state machine, evaluating architecture diagrams, capacity estimations, and component trade-offs.
    - **Behavioral Scoring:** Evaluates STAR method completeness and ownership language.
11. **Post-Session Debriefs & Learning Loop:**
    - Generates evidence-backed debriefs highlighting strengths, weaknesses, and key quotes.
    - Automatically converts detected weaknesses into SM-2 study cards with spaced repetition review intervals.
12. **Data Lifecycle & Compliance:**
    - Asynchronous GDPR data export worker generates encrypted ZIP archives.
    - Irreversible cascading account deletion purges database records and object storage blobs.

---

## 3. How an External Frontend Consumes PRAXIS

A client platform can be developed in Flutter, React Native, Swift, Kotlin, Vue, or terminal CLI by implementing standard HTTP/WebSocket clients:

### 3.1 Authentication Handshake
1. Client obtains a JWT token from Supabase Auth (or test token in dev mode).
2. All REST requests must pass the token in the HTTP header:
   ```http
   Authorization: Bearer <access_token>
   ```
3. The backend returns candidate context at `GET /api/v1/candidates/me`.

### 3.2 Realtime Interview Session Flow
1. **Create Session:** Client calls `POST /api/v1/sessions` with `interview_type`, `role`, and `difficulty`.
2. **Connect WebSocket:** Client opens a binary WebSocket to `wss://<host>/ws/sessions/{session_id}?token=<jwt>`.
3. **Capture & Stream Audio:**
   - Client records microphone audio at 16,000 Hz, 1 channel, 16-bit PCM.
   - Packs 32ms audio chunks (1024 bytes) into the 18-byte binary format:
     ```
     Header: [ver: 1, type: 1, seq: uint32, ts: float64, len: 1024] + PCM16 samples
     ```
4. **Receive Feedback:**
   - Every second, receives `coaching.metrics` JSON event with live WPM and filler word alerts.
   - When speaking ends, receives `transcript.final` and `interviewer.text` with synthesized audio.
5. **Debrief:** Client calls `GET /api/v1/sessions/{id}/debrief` to display final scores and review flashcards.

---

## 4. Documented Deployment Boundary

The backend is packaged into 4 independent, immutable container images:
1. `praxis-api`: Serves the REST API (`backend/app/main.py`), OpenAPI docs, and admin routers.
2. `praxis-realtime`: Serves the WebSocket session orchestrator (`realtime_agent/app/main.py`).
3. `praxis-worker`: Executes ARQ asynchronous background jobs (`backend/app/worker_tasks.py`).
4. `praxis-sandbox`: Dedicated internal execution microservice for candidate coding drills.

All inter-service communication between the API, worker, and realtime agents uses Redis queues and the authoritative PostgreSQL database. No local filesystem sharing is required across containers.
