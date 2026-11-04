# PRAXIS InterviewOS — Master Environment Variables Reference

**Specification Standard:** Strictly validated by Pydantic v2 `Settings` class (`packages/config/settings.py`).  
**Secret Hygiene:** Plaintext secret values must never be checked into version control. In staging and production, secrets are injected exclusively via Google Secret Manager.

---

## 1. Application & Environment Mode Settings

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `APP_ENV` | `str` | `"development"` | Yes | Runtime environment: `"development"`, `"staging"`, or `"production"`. Controls CSP strictness and error masking. |
| `ZERO_SPEND_MODE` | `bool` | `true` | Optional | If `true`, restricts AI Gateway routing exclusively to free-tier cloud models (`llama-3.3-70b-versatile`, `gemini-2.5-flash`). |
| `LOCAL_ONLY_MODE` | `bool` | `false` | Optional | If `true`, disables all outbound internet connections; forces local Ollama, Whisper, and BGE models. |
| `LOG_LEVEL` | `str` | `"INFO"` | Optional | Logging verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`. Emitted as structured JSON in production. |
| `AUTH_DEV_BYPASS` | `bool` | `false` | **FORBIDDEN** | Development-only authentication bypass. Must be `false` or unset in production. |

---

## 2. Database & Persistence Configuration

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `DATABASE_URL` | `str` | — | Yes | PostgreSQL connection string (`postgresql+asyncpg://user:pass@host:5432/praxis`). |
| `SUPABASE_POOLER_URL` | `str` | `""` | Optional | Transaction pooler URL (e.g. Supabase PgBouncer / Supavisor). |
| `DB_POOL_SIZE` | `int` | `20` | Optional | Maximum number of permanent connections held in SQLAlchemy asyncpg pool. |
| `DB_MAX_OVERFLOW` | `int` | `10` | Optional | Maximum temporary connections allowed during traffic bursts above pool size. |
| `DB_POOL_TIMEOUT_S` | `float` | `30.0` | Optional | Seconds to wait for an available connection from the pool before raising an error. |
| `DB_POOL_PRE_PING` | `bool` | `true` | Optional | Tests connection liveness with `SELECT 1` before checkout to discard dead sockets. |
| `DB_STATEMENT_TIMEOUT_MS`| `int` | `5000` | Optional | Statement timeout in milliseconds applied to application queries to prevent table locks. |

---

## 3. Redis, Caching & Queue Configuration

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `REDIS_URL` | `str` | `"redis://localhost:6379/0"` | Yes | Redis connection string for rate limiting, session state, and ARQ queue. |
| `REDIS_MAX_CONNECTIONS`| `int` | `50` | Optional | Connection pool ceiling for Redis async client. |
| `REDIS_SOCKET_TIMEOUT_S`| `float`| `5.0` | Optional | Network socket timeout for Redis commands. |
| `ARQ_QUEUE_NAME` | `str` | `"praxis:queue"` | Optional | Redis key prefix for ARQ asynchronous task queue. |
| `WORKER_MAX_JOBS` | `int` | `10` | Optional | Maximum concurrent background jobs processed per worker container instance. |

---

## 4. Authentication & JWT Validation

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `SUPABASE_URL` | `str` | `""` | Yes | Supabase project URL (e.g. `https://xyz.supabase.co`). |
| `SUPABASE_JWT_SECRET` | `str` | `""` | Yes | 256-bit symmetric secret used to verify HS256 tokens in local development. |
| `SUPABASE_JWKS_URL` | `str` | `""` | Optional | Public JWKS endpoint for asymmetric RS256 token verification. |
| `JWT_AUDIENCE` | `str` | `"authenticated"` | Optional | Expected JWT audience claim (`aud`). |
| `JWT_LEEWAY_S` | `int` | `60` | Optional | Clock skew tolerance window in seconds for expiration checks. |

---

## 5. AI Gateway & Provider Credentials

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `GROQ_API_KEY` | `str` | `""` | Optional | API key for Groq LPUs (`gsk_...`). Provides free-tier `llama-3.3-70b-versatile`. |
| `GEMINI_API_KEY` | `str` | `""` | Optional | API key for Google Gemini (`AIzaSy...`). Provides free-tier `gemini-2.5-flash`. |
| `OPENAI_API_KEY` | `str` | `""` | Optional | API key for OpenAI (`sk-proj-...`). |
| `ANTHROPIC_API_KEY` | `str` | `""` | Optional | API key for Anthropic Claude (`sk-ant-...`). |
| `DEEPSEEK_API_KEY` | `str` | `""` | Optional | API key for DeepSeek (`sk-...`). |
| `FREE_TIER_BUDGET_DAILY_USD`| `float`| `10.0` | Optional | Daily dollar ceiling for AI provider API spend across all users. |

---

## 6. Realtime Audio & WebSocket Configuration

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `WS_AUTH_TIMEOUT_S` | `float` | `5.0` | Optional | Seconds allowed for client to send authentication JWT after WebSocket connection. |
| `WS_RECONNECT_GRACE_S`| `float` | `30.0` | Optional | Grace period window for dropped clients to reconnect without state loss. |
| `LOCAL_STT_MODEL` | `str` | `"tiny.en"` | Optional | Faster-Whisper model size (`"tiny.en"`, `"small"`, `"base"`). |
| `LOCAL_EMBEDDING_MODEL`| `str` | `"BAAI/bge-small-en-v1.5"`| Optional | HuggingFace embedding model ID (384-dimensional dense vectors). |

---

## 7. Object Storage Configuration

| Variable Name | Type | Default | Required in Prod | Description & Impact |
|---|---|---|---|---|
| `STORAGE_BACKEND` | `str` | `"local"` | Yes (`"gcs"`) | Storage adapter: `"local"` (disk) or `"gcs"` (Google Cloud Storage). |
| `STORAGE_BUCKET` | `str` | `"praxis-uploads"` | Yes | Google Cloud Storage private bucket name. |
| `MAX_UPLOAD_BYTES` | `int` | `10485760` | Optional | Maximum allowed file upload payload size (10 MB). |
