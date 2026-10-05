# PRAXIS AI Model Catalog

All AI models used by PRAXIS, their purpose, routing, and cost characteristics.
Source of truth: `config/models.yaml` and `packages/ai-gateway/praxis_ai_gateway/`.

---

## 1. Model Registry

The `ModelRegistry` class (`packages/ai-gateway/praxis_ai_gateway/registry.py`) loads
`config/models.yaml` at startup. It resolves "task aliases" to ordered candidate lists.
The `GatewayRouter` iterates candidates in order, skipping those with open circuit breakers
or insufficient capabilities. Provider names in `models.yaml` must match registered
provider instances.

Placeholder guard: if any model entry contains `<VERIFY_AT_BUILD>`, the registry raises
`ConfigurationError` at startup — preventing deployment with unresolved model names.

---

## 2. Local Models

### Silero VAD (ONNX)

| Property | Value |
|---|---|
| Purpose | Voice Activity Detection — detect speech vs. silence in real-time audio |
| Runtime | ONNX via `onnxruntime` in the `praxis-realtime` Docker image |
| Package | `silero-vad==5.1.2` |
| Input | 16 kHz mono audio frames (32ms chunks) |
| Output | Binary speech/silence decision + probability per chunk |
| Context window | N/A (frame-level) |
| Cost | Free (on-device) |
| Availability | Always-on in realtime service; no cloud fallback |
| Baked in image | Yes — `RUN python -c "import silero_vad; silero_vad.load_silero_vad()"` at build time |

### faster-whisper (base.en)

| Property | Value |
|---|---|
| Purpose | Speech-to-text transcription |
| Runtime | `faster-whisper==1.1.0` (CTranslate2 backend) on CPU/int8 |
| Model | `base.en` — English-only, ~74M parameters |
| Input | Audio chunks after VAD gating |
| Output | Text transcript with word-level timestamps |
| Context window | ~30 seconds per segment |
| Cost | Free (on-device) |
| Cloud fallback | Groq Whisper (routed via `praxis_ai_gateway.transcription.router`) |
| Baked in image | Yes — `WhisperModel('base.en', device='cpu', compute_type='int8')` at build |

### Piper TTS

| Property | Value |
|---|---|
| Purpose | Text-to-speech synthesis for interviewer voice |
| Runtime | Piper TTS (referenced in realtime-agent; local ONNX inference) |
| Input | Text string |
| Output | WAV audio bytes (streamable) |
| Cost | Free (on-device) |
| Availability | Local only; no cloud fallback in current config |

### bge-small-en-v1.5 (sentence-transformers)

| Property | Value |
|---|---|
| Purpose | Semantic embeddings for RAG (resume chunks, question bank) |
| Package | `sentence-transformers==3.3.1`, `torch==2.5.1+cpu` |
| Dimensions | 384 |
| Input | Text string (up to ~512 tokens) |
| Output | `vector(384)` stored in `document_chunks.embedding` |
| Cost | Free (on-device) |
| Fallback | If embedding fails on final retry, worker stores chunks without embeddings and falls back to FTS-only search. |
| Used by | `process_resume` ARQ job via `backend/app/services/document_processing.py` |

---

## 3. Cloud Models

All cloud models are routed through `GatewayRouter`. Access requires the corresponding
API key env var to be present at startup; missing providers are silently skipped.

### Task alias: `fast_classify`

Purpose: Low-latency classification tasks (e.g. intent detection, routing decisions).

| Priority | Provider | Model | Max latency | Cost (per 1k tokens in/out) |
|---|---|---|---|---|
| 1 | ollama (local) | `llama3.1:8b-instruct-q4_K_M` | 500ms | Free |
| 2 | Groq | `llama-3.1-8b-instant` | 1000ms | Free tier |
| 3 | OpenAI | `gpt-4o-mini` | 2000ms | $0.00015 / $0.00060 |

### Task alias: `reasoning`

Purpose: Structured extraction and drafting — resume parsing, JD analysis, study material
generation, outreach drafts. Most worker jobs use this alias with `zero_spend_mode=True`,
which forces local/free providers.

| Priority | Provider | Model | Max latency | Cost (per 1k tokens in/out) |
|---|---|---|---|---|
| 1 | ollama (local) | `llama3.1:8b-instruct-q4_K_M` | 30000ms | Free |
| 2 | Groq | `llama-3.3-70b-versatile` | 10000ms | Free tier |
| 3 | OpenAI | `gpt-4o-mini` | 10000ms | $0.00015 / $0.00060 |

### Task alias: `deep_reasoning`

Purpose: High-stakes decisions requiring stronger models — final scoring, complex system
design evaluation.

| Priority | Provider | Model | Max latency | Cost (per 1k tokens in/out) |
|---|---|---|---|---|
| 1 | OpenAI | `gpt-4o` | 10000ms | $0.00500 / $0.01500 |
| 2 | Anthropic | `claude-3-5-sonnet-20240620` | 10000ms | $0.00300 / $0.01500 |
| 3 | Groq | `llama-3.3-70b-versatile` | 10000ms | Free tier |
| 4 | ollama (local) | `llama3.1:8b-instruct-q4_K_M` | 30000ms | Free |

### Task alias: `stt_stream`

Purpose: Cloud STT fallback when local faster-whisper is unavailable.
Routed by `praxis_ai_gateway.transcription.router`, not by `GatewayRouter`.

| Priority | Provider | Model |
|---|---|---|
| 1 | local | `faster-whisper-small.en` |

---

## 4. Configured but Not Listed in models.yaml

The following providers are supported (implementations exist in
`packages/ai-gateway/praxis_ai_gateway/providers/`) but are not currently in
`config/models.yaml`:

- Gemini (`gemini.py`) — `GEMINI_API_KEY` required
- Anthropic (`anthropic.py`) — `ANTHROPIC_API_KEY` required; used in `deep_reasoning`
- DeepSeek (`deepseek.py`) — `DEEPSEEK_API_KEY` required
- xAI Grok (`xai.py`) — `XAI_API_KEY` required

Providers missing their API key env var are skipped silently at startup (logged at WARNING).

---

## 5. Budget Guard

`packages/ai-gateway/praxis_ai_gateway/budget.py` enforces spend limits before every
billable call.

| Limit | Default | Scope |
|---|---|---|
| Session cap | $1.00 | Per `session_id` per day |
| Daily cap | $5.00 | Per `user_id` per UTC day |

Both limits are tracked in Redis with 24h TTL keys. Exceeding either raises
`BudgetExceededError` before the API call is made — no charge is incurred.

Paid provider consent: first paid call requires either prior paid usage or
`profiles.paid_provider_acknowledged = true`. Fails closed (treats as no consent)
if the DB is unavailable, causing the router to skip to the next free candidate.

---

## 6. Version Tracking

`turn_scores.rubric_version` stores the rubric version string used to generate each score.
This allows historical comparison when the scoring rubric changes and ensures scores are
never silently mixed across incompatible rubric versions.

`document_chunks.embedding_model` and `document_chunks.embedding_version` track which
embedding model produced each vector, enabling targeted re-embedding when models change.

---

## 7. Circuit Breaker

`packages/ai-gateway/praxis_ai_gateway/resilience.CircuitBreaker` wraps every provider
call. States: `closed → open → half_open`. State is persisted to `provider_health` table
and Redis for durability across restarts. An open circuit breaker causes the router to skip
that provider and fall back to the next candidate in the alias list.

---

## 8. Structured Output Guarantee

All calls using `method_name="structured"` return a validated Pydantic model. The gateway
passes a `schema` parameter to the provider, which uses function-calling / JSON mode
where available. On validation failure, the gateway retries up to `max_tries` times before
propagating the error.
