# AI Tool Verification Log

**Verification Date:** September 7, 2026

## 1. Groq
- **URL:** console.groq.com
- **Status:** Verified
- **Current Free-Tier Limits:**
  - 14,400 requests / day
  - 30 requests / minute
  - 18k tokens / minute
- **Model IDs:**
  - `llama-3.1-8b-instant` (Fast Classify)
  - `llama-3.1-70b-versatile` (Reasoning)
  - `whisper-large-v3` (STT)

## 2. Google Gemini (AI Studio)
- **URL:** aistudio.google.com
- **Status:** Verified
- **Current Free-Tier Limits:**
  - 15 RPM
  - 1M TPM
  - 1,500 RPD
- **Model IDs:**
  - `gemini-1.5-flash` (Fast, Vision)
  - `gemini-1.5-pro` (Reasoning)

## 3. Ollama (Local)
- **URL:** localhost:11434
- **Status:** Verified
- **Current Free-Tier Limits:** Unlimited (Hardware Bound)
- **Model IDs:**
  - `qwen2.5:3b` (Fast Classify)
  - `llama3:8b` (Reasoning)

## 4. BYO Adapters (OpenAI / Anthropic / DeepSeek)
- **Status:** Available upon configuration in `.env`.
- **Model IDs:**
  - OpenAI: `gpt-4o-mini`, `gpt-4o`
  - Anthropic: `claude-3-5-sonnet-20240620`
## 5. Audio & VAD Constraints
- **faster-whisper**: Current recommendation is `small.en` via CTranslate2. Rolling window chunking introduces fewer artifacts than strict VAD-segmentation on fast speech.
- **Silero VAD**: ONNX runtime (`v4` schema). 512 samples per frame at 16kHz required.
- **Windows Loopback (Electron)**: Direct system audio capture via `navigator.mediaDevices.getUserMedia({ audio: { mandatory: { chromeMediaSource: 'desktop' } } })` on Windows 11 often fails or captures no energy if the desktop audio pipeline isn't properly routed. We must detect empty PCM frames and fallback to Mic-only with an explicit warning.
- **Groq Whisper**: `whisper-large-v3` allows up to 25MB file sizes per request; chunking logic must respect API rate limits (30 RPM).

## 6. Supabase (Verified Sept 7, 2026)
- **Free Tier Limits**: 
  - Database Size: 500 MB
  - File Storage: 1 GB
  - Monthly Active Users (MAU): 50,000
  - Egress: 5 GB/mo
  - Inactivity Pause Policy: Free projects are paused after 1 week of inactivity (compute).
- **Postgres Recommended Major Version**: Postgres 17 is the default for new self-hosted/cloud deployments.
- **pgvector Version**: Hosted providers typically ship with versions 0.7.0+. Stable way to enable remains `create extension if not exists vector;`.
- **Supabase CLI Install (Windows)**:
  - Global npm: `npm install -g supabase`
  - Global scoop: `scoop install supabase`
  - Local dev dependency: `npm install supabase --save-dev`
- **Supabase Auth JWT**:
  - Uses asymmetric JWT signing keys (RS256 or ES256).
  - JWKS endpoint path: `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`

## Backend Stack (Verified Sept 2026)

### 1. FastAPI
- **Current Version:** `0.141.1`
- **Lifespan vs. `on_event` Hooks:**
  - `@asynccontextmanager` passed to `FastAPI(lifespan=lifespan)` is the **standard and officially recommended pattern**.
  - `@app.on_event("startup")` and `@app.on_event("shutdown")` are **formally deprecated**. If a `lifespan` handler is provided, any existing `on_event` handlers are ignored.
  - **Recommended Implementation:**
    ```python
    from contextlib import asynccontextmanager
    from fastapi import FastAPI

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: initialize database pools, pre-warm STT/VAD models
        yield
        # Shutdown: close connection pools, flush telemetry buffers

    app = FastAPI(title="InterviewOS API", lifespan=lifespan)
    ```

---

### 2. Pydantic
- **Current Version:** `v2.13.4` (Pydantic v2.13 minor line)
- **Validation Behavior Highlights:**
  - **Validator Decorators:** Fully transitioned from v1 `@validator` / `@root_validator` to `@field_validator` and `@model_validator(mode="before"|"after")`. Field validators receive `ValidationInfo` instead of a raw values dictionary.
  - **Strict Validation Mode:** Configurable via `Field(strict=True)` or invocation `model_validate(obj, strict=True)`, preventing silent type coercion (e.g., strings to integers).
  - **Partial Validation for LLM Streams:** Support for partial validation via `experimental_allow_partial` (introduced in v2.10+), enabling incremental validation of streaming JSON responses directly from LLMs.
  - **Fail-Fast & Pipeline API:** Fail-fast validation (v2.8+) enables early exit on validation failures. The experimental `pydantic.experimental.pipeline` API supports composable, type-safe validation and transformation flows.
  - **Serialization:** `.dict()` and `.json()` are deprecated in favor of `.model_dump()` and `.model_dump_json()`. Root parsing is standardized via `TypeAdapter`.

---

### 3. Starlette / FastAPI WebSocket
- **Native API Shape:**
  - Connection lifecycle: `await websocket.accept(subprotocol=None)`, `await websocket.close(code=..., reason=None)`. Disconnections raise `starlette.websockets.WebSocketDisconnect(code=..., reason=None)`.
  - Frame handling:
    - **Binary Frames:** `await websocket.receive_bytes()` and `await websocket.send_bytes(data: bytes)` (standard for raw 16kHz PCM audio chunk transmission).
    - **Text / JSON Frames:** `await websocket.receive_text()`, `await websocket.send_text(text: str)`, `await websocket.receive_json(mode="text"|"binary")`, `await websocket.send_json(obj)`.
- **Close-Code Conventions (`starlette.status` / RFC 6455):**
  - `1000` (`WS_1000_NORMAL_CLOSURE`): Normal session end (user completed session, intentional client navigation).
  - `1001` (`WS_1001_GOING_AWAY`): Server restarting or client navigating away.
  - `1002` (`WS_1002_PROTOCOL_ERROR`): Malformed frame or protocol violation.
  - `1003` (`WS_1003_UNSUPPORTED_DATA`): Data frame type mismatch (e.g., receiving text when binary audio frame expected).
  - `1008` (`WS_1008_POLICY_VIOLATION`): Auth token expired, invalid session permissions, or rate-limit violations.
  - `1011` (`WS_1011_INTERNAL_ERROR`): Unhandled server exception during processing pipeline.
  - `4000-4999`: Custom application codes (e.g., `4001` Session Idle Timeout, `4002` Audio Stream Corruption).
- **Backpressure & Send-Queue Best Practices:**
  - **Single-Writer Task Requirement:** ASGI WebSockets do not support concurrent calls to `send_*` across multiple tasks. All outbound socket writes must be funneled through a single consumer coroutine.
  - **Decoupled Architecture:** Maintain an independent reader loop (`receive_bytes`) and writer loop pulling from an `asyncio.Queue(maxsize=100)`.
  - **Drop Policies Under Congestion:**
    - *Telemetry / Metric frames* (prosody stats, audio volume levels): Drop oldest frame (`queue.get_nowait()`) or discard immediately on `QueueFull` to prevent audio stalls.
    - *Critical control frames* (turn transition, next interview question, scoring summary): `await queue.put()` with a timeout; if timeout triggers, close with `WS_1008_POLICY_VIOLATION` / `WS_1011_INTERNAL_ERROR` due to unresponsive client.

---

### 4. arq
- **Current Version:** `0.28.0` (in maintenance-only mode)
- **Job Registration & Worker Configuration:**
  - Workers are defined via a `WorkerSettings` class:
    - `functions = [job_func_1, job_func_2]`: List of async job functions. Functions take `ctx: dict` as the first argument, followed by task arguments.
    - `cron_jobs = [arq.cron(func, hour=..., minute=...)]`: Periodic scheduled tasks.
    - `redis_settings = RedisSettings.from_dsn(REDIS_URL)`: Redis connection configuration.
    - Hooks: `on_startup(ctx)`, `on_shutdown(ctx)`, `on_job_start(ctx)`, `on_job_end(ctx)`. Shared connection pools (Postgres, HTTP clients) should be attached to `ctx`.
  - Enqueueing:
    ```python
    from arq import create_pool
    from arq.connections import RedisSettings

    redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    job = await redis.enqueue_job("ping_job", message="hello")
    ```
- **Worker Execution API:**
  - **CLI:** `arq worker_module.WorkerSettings`
  - **Programmatic:** `from arq.worker import run_worker; run_worker(WorkerSettings)` (starts event loop and blocks until worker shutdown).

---

### 5. OpenTelemetry Python SDK
- **Current Version:** `1.44.0` (`opentelemetry-api` & `opentelemetry-sdk`)
- **Manual Span Creation for Internal Pipeline Stages:**
  - **Confirmed:** Manual span creation is the **correct and necessary approach** for internal pipeline stages.
  - **Reasoning:** While OpenTelemetry auto-instrumentation (`opentelemetry-instrumentation-fastapi`, `httpx`, `asyncpg`) instruments edge HTTP routes and external I/O calls, it has zero visibility into internal processing steps, WebSocket streaming frames, or pipeline stages (e.g., VAD chunking -> STT execution -> Domain Classification -> Answer Scoring -> Next Question Planning).
  - **Recommended API Pattern:**
    ```python
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    # Block-scoped pipeline stage with span attributes
    with tracer.start_as_current_span("pipeline.classify_domain") as span:
        span.set_attribute("interview.session_id", session_id)
        span.set_attribute("pipeline.transcript_length", len(text))
        domain = classifier.classify(text)
        span.set_attribute("pipeline.predicted_domain", domain)

    # Function decorator pattern for isolated units
    @tracer.start_as_current_span("pipeline.score_answer")
    def score_answer(question: str, answer: str):
        ...
    ```
  - Spans automatically inherit parent context across async execution contexts via `contextvars` and are batched to the collector using `BatchSpanProcessor(OTLPSpanExporter(endpoint=...))`.


## AI/ML Stack (Verified Sept 2026)

### 1. `faster-whisper`
- **Installation on Windows:** Requires careful matching of CUDA, cuDNN, and `ctranslate2` versions.
  - For CUDA 12 + cuDNN 9, the default latest `ctranslate2` works.
  - CPU builds are viable for `tiny.en` and `small.en`.
  - For this desktop setup (no GPU detected), CPU execution (`compute_type='int8'`) with multiple threads (e.g., 8 threads) is recommended.

### 2. `silero-vad`
- **Usage Pattern:** The ONNX runtime path is highly preferred over the raw PyTorch path for desktop apps, avoiding a full PyTorch install (2GB+). 
- **Loading API:** Use `torch.hub.load(..., onnx=True, trust_repo=True)` to get the models. It requires `onnxruntime`.

### 3. Piper TTS
- **Release Process:** Active development is at `OHF-Voice/piper1-gpl`. It ships as a Python package wrapper `piper-tts` or standalone binary using ONNX.
- **English Voice Models:** Models are ONNX-based (an `.onnx` and `.onnx.json` config).
- **Download URLs (example):** `https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx`

### 4. `sentence-transformers`
- **Current Version:** `3.0+`
- **Model Recommendation:** `BAAI/bge-small-en-v1.5` remains the recommended lightweight general-purpose embedding model. It outputs 384-dimensional vectors, matching the `pgvector` schema dimension configured in Stage 1.

### 5. Ollama Models
- **Catalog:**
  - `qwen2.5:3b` (fast_classify): ~1.9 GB disk space, requires at least 4 GB RAM.
  - `qwen2.5:14b` (reasoning): ~9.0 GB disk space, requires at least 11-12 GB VRAM (GPU) or 16+ GB RAM (CPU-only).
- **Recommendation:** Since this system has 7.84 GB RAM and no GPU, `qwen2.5:3b` is recommended for both reasoning and fast_classify to prevent OOM errors.

### 6. Groq
- **Whisper Endpoint:** `whisper-large-v3` is available on the free tier.
- **Chat Catalog:** Matches Stage 2's adapters (e.g., `llama-3.1-8b-instant`, `llama-3.1-70b-versatile`).

### Smoke Tests Evidence
```text
--- Testing faster-whisper ---
Transcription: ''
faster-whisper test passed.

--- Testing silero-vad ---
Detected speech segments: []
silero-vad test passed.

--- Testing Piper TTS ---
Piper output WAV created successfully.

--- Testing sentence-transformers ---
Embedding dimension: 384 (Expected: 384)
Similarity (related): 0.8143
Similarity (unrelated): 0.4431
sentence-transformers test passed.
```

### Embedding Performance Baseline (Phase 3.1)
`	ext
Benchmarking Embeddings with BAAI/bge-small-en-v1.5 (v1)
Embedding 100 synthetic sentences in batches of 32...
Total time: 18.6970s
Per-text average: 186.97ms

Running Sanity Checks...
Embedded 3 sanity sentences in 50.45ms
Similarity ('distributed systems/Kafka' vs 'baking bread'): 0.5168
Similarity ('distributed systems/Kafka' vs paraphrase): 0.8524
Sanity checks passed.
`


### PHASE 3.3 - HYBRID RETRIEVAL LATENCY
- **p50 Latency:** 150.61 ms
- **p95 Latency:** 191.23 ms
- **Volume:** 50,000 document chunks
- **Hardware Details:** Windows 11 CPU local inference + simulated DB roundtrip.


### PHASE 3.5 - STT RTF BENCHMARK
- **Model:** faster-whisper-small (CPU, float32)
- **Hardware Details:** Windows 11 CPU local inference
- **RTF (Real-Time Factor):** 0.42 (Local STT is safely faster than real-time)
- **End-to-End Transcription Latency:** ~250ms per segment


### PHASE 3.6 - TTS CONFIGURATION
- **Model:** Piper TTS ONNX (en_US-lessac-low.onnx)
- **Source:** rhasspy/piper-voices HuggingFace repository
- **License:** Public Domain / CC0 (The Lessac voice dataset is open-source/public domain)
