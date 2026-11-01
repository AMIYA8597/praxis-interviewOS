# PRAXIS Phase 1 — Production Backend & Database Architecture

## 1. System Overview & Product Mission

PRAXIS is a multimodal interview intelligence, mock-practice, and personalized learning platform. It operates exclusively as an interview preparation platform designed to listen to and coach the **candidate** during practice sessions.

Per `docs/PRODUCT_SPEC.md` (ADR-001), PRAXIS is strictly prohibited from supporting real employer interview proctoring evasion, hidden capture, stealth windows, or bypass mechanisms.

```mermaid
flowchart TD
    subgraph Clients["External Clients (Phase 3)"]
        WebClient["Web Client (Next.js)"]
        DesktopClient["Desktop Client (Electron)"]
    end

    subgraph GCP["Google Cloud Platform (Compute Layer)"]
        CoreAPI["Core REST API\n(FastAPI / Uvicorn)\n[Port 8000]"]
        RealtimeAgent["Realtime Agent\n(WebSocket / Uvicorn)\n[Port 8080]"]
        ARQWorker["Background Worker\n(ARQ / Python)\n[Port 8080 Health]"]
        Sandbox["Coding Sandbox\n(FastAPI / Minimal)\n[Port 8001]"]
    end

    subgraph DataPlane["Data & State Plane"]
        SupabaseDB[("Supabase PostgreSQL 17\n+ pgvector\n+ RLS Policies")]
        SupabaseAuth["Supabase Auth\n(JWKS RS256 / HS256)"]
        SupabaseStorage["Supabase Storage\n(Encrypted Buckets)"]
        RedisInstance[("Memorystore Redis 7\n(ARQ Queue + State + Cache)")]
    end

    subgraph ModelGateway["AI Gateway (Phase 2 Interface)"]
        AIGateway["AI Gateway\n(packages/ai-gateway)"]
        OllamaProvider["Local Ollama\n(bge-small / Whisper)"]
        CloudProviders["Cloud Providers\n(Groq / Gemini / OpenAI)"]
    end

    WebClient -->|HTTPS REST| CoreAPI
    DesktopClient -->|HTTPS REST| CoreAPI
    DesktopClient -->|WSS Binary PCM16| RealtimeAgent

    CoreAPI -->|Auth Verification| SupabaseAuth
    CoreAPI -->|Transaction Pooler (5432/6543)| SupabaseDB
    CoreAPI -->|Enqueue Jobs| RedisInstance
    CoreAPI -->|Signed Uploads| SupabaseStorage

    RealtimeAgent -->|Session State & VAD| RedisInstance
    RealtimeAgent -->|Transcribe / Synthesize| AIGateway
    RealtimeAgent -->|Persist Turns & Scores| SupabaseDB

    ARQWorker -->|Dequeue Jobs| RedisInstance
    ARQWorker -->|Parse & Embed| AIGateway
    ARQWorker -->|Durable Persistence| SupabaseDB

    AIGateway --> OllamaProvider
    AIGateway --> CloudProviders
```

---

## 2. Service Separation & Compute Units

The backend architecture consists of four distinct, independently scalable deployment units on Google Cloud Run:

### 2.1 Core REST API (`docker/Dockerfile.api`)
- **Framework**: FastAPI running under Uvicorn with lifespan management.
- **Responsibilities**: Candidate onboarding, profile management, resume uploads, job description ingestion, preparation plans, session CRUD, analytics, and admin operations.
- **Port**: `8000` (or dynamic `$PORT`).
- **Health Endpoints**:
  - `/health/live`: 200 OK liveness check.
  - `/health/ready`: Validates live PostgreSQL and Redis connectivity.
  - `/health/startup`: Validates DB connectivity and verifies all 31 migrations in `supabase/migrations/` have been recorded in `schema_migrations`.
- **Metrics**: Protected Prometheus `/metrics` endpoint requiring Basic Auth or Bearer token authentication.

### 2.2 Realtime WebSocket Agent (`docker/Dockerfile.realtime`)
- **Protocol**: Binary WebSocket receiving 16-bit PCM mono 16 kHz audio frames.
- **Responsibilities**: Live practice interview orchestration, real-time Voice Activity Detection (Silero VAD), local Speech-to-Text (faster-whisper), conversational turn state machine, coaching metric accumulation, and debrief generation.
- **Port**: `8080`.
- **Lifecycle & Resilience**: Disconnected sessions preserve state in Redis (`session:state:<id>`) for a 30-second grace window (`WS_RECONNECT_GRACE_S`), allowing seamless desktop client reconnects without session termination.

### 2.3 Background ARQ Worker (`docker/Dockerfile.worker`)
- **Framework**: ARQ (Async Redis Queue) running `backend.worker_settings.WorkerSettings`.
- **Responsibilities**: Asynchronous document text extraction (PDF, DOCX via tesseract-ocr/pdfplumber), document chunking, vector embedding generation, job blueprint extraction, SM-2 spaced repetition card generation, and automated retention cleanup.
- **Health Server**: Embedded HTTP health server running on `$PORT` answering `/health/live` to fulfill Cloud Run container health contract.
- **Reliability**: Exponential backoff, maximum 3 retries, dead-letter recording, and transaction-safe idempotency keys.

### 2.4 Isolated Execution Sandbox (`docker/Dockerfile.sandbox`)
- **Responsibilities**: Isolated execution of untrusted candidate code during coding practice sessions with zero application credentials, no internal network egress, and restricted syscalls.
- **Port**: `8001`.

---

## 3. Database Architecture & Supabase Integration

### 3.1 Single Source of Truth Migrations
- Migration files are strictly maintained in `supabase/migrations/*.sql` (31 chronological files).
- Legacy Alembic revisions in `backend/alembic/versions` are officially retired (`backend/alembic/versions/README.md` documents retirement).
- Zero duplicate version prefixes exist across all migrations.
- `scripts/migrate.py` applies migrations idempotently, bootstrapping tracking via `20260908000001_migration_tracking.sql` and logging execution timing in `migration_status`.

### 3.2 PgBouncer Connection Pooler Compatibility
- When connecting from Cloud Run to Supabase, queries run through Supabase PgBouncer pooler in transaction mode.
- Standard asyncpg caches prepared statements client-side by query string, which causes fatal `DuplicatePreparedStatementError` when PgBouncer switches physical connections between transactions.
- **Resolution**: `backend/app/db/session.py` explicitly disables the statement cache:
  ```python
  connect_args = {
      "statement_cache_size": 0,
      "prepared_statement_cache_size": 0,
  }
  ```

### 3.3 Connection Budgeting
- Under the Supabase connection budget ([docs/DATABASE_CONNECTION_BUDGET.md](file:///d:/work/interviewOS/docs/DATABASE_CONNECTION_BUDGET.md)), settings enforce:
  - `DB_POOL_SIZE = 2`
  - `DB_MAX_OVERFLOW = 3`
- Total connections per service instance are capped at 5, ensuring that concurrent Cloud Run scaling across API, Realtime Agent, and Worker services stays well below Supabase pooled limits.

---

## 4. Auth & Row-Level Security (RLS)

1. **Cryptographic JWT Verification**:
   - Access tokens from Supabase Auth are cryptographically verified via RS256 against `${SUPABASE_URL}/auth/v1/.well-known/jwks.json`.
   - JWKS keys are cached in Redis for `JWKS_CACHE_TTL_S` (3600s), with rate-limited refresh protection (`JWKS_REFRESH_COOLDOWN_S = 60s`).
   - Legacy HS256 tokens are supported as a fallback when `SUPABASE_JWT_SECRET` is configured.
2. **Transaction-Local RLS Identity**:
   - The verified `sub` claim is injected per-transaction into Postgres session configuration:
     ```sql
     SELECT set_config('request.jwt.claims', :claims, true);
     ```
   - Setting the third parameter to `true` ensures claims are strictly transaction-scoped, preventing identity leakage across pooled database connections.
   - Forged or unverified tokens never set claims, causing all tenant queries to return 0 rows.
3. **Application Defense-in-Depth**:
   - In addition to PostgreSQL RLS, every candidate-scoped route explicitly validates tenant ownership in application queries to eliminate Insecure Direct Object References (IDOR).

---

## 5. Observability & Observability Architecture

- **Correlation Context**: Every request assigns an `X-Request-ID` and captures `trace_id`, `user_id`, `candidate_id`, and `session_id` into Python `contextvars`.
- **Structured JSON Logging**: Logs in staging and production emit standard JSON with correlation identifiers, ISO 8601 timestamps, severity levels, and service names.
- **PII & Credential Redaction**: All log records filter and redact sensitive keys:
  - Tokens: `access_token`, `refresh_token`, `authorization`, `jwt`, `api_key`
  - Credentials: `password`, `secret`, `service_role_key`
  - Personal Data: `email`, `user_email`, `phone`, `phone_number`, `ssn`, `credit_card`, raw resume text
- **OpenTelemetry Tracing**: Distributed tracing instrumentation hooks into FastAPI, SQLAlchemy, and asyncpg, exporting via OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT`).
