# AI Model Registry

Source of truth for every AI model PRAXIS backend consumes at runtime.
Models are configured in `config/models.yaml`; this document is the human-readable
canonical registry with capability, cost, and risk metadata.

---

## Registry format

Each entry lists: alias → provider model ID, capability class, data-trust level,
latency SLO, cost tier, and the PRAXIS prompt paths that use the alias.

---

## Active models (staging-validated)

| Alias | Provider | Model ID | Capability | Trust | p95 Latency | Cost Tier |
|-------|----------|----------|------------|-------|-------------|-----------|
| `reasoning` | Configurable (Anthropic / OpenAI / Gemini) | See `config/models.yaml` | Long-form reasoning, structured output | UNTRUSTED inputs isolated via `PromptBuilder.add_untrusted()` | < 8 s | Medium |
| `fast` | Configurable | See `config/models.yaml` | Short completions, classification | Same | < 2 s | Low |
| `vision` | Configurable | See `config/models.yaml` | Image OCR + classification | Same | < 5 s | Medium |
| `embeddings` | HuggingFace local | BAAI/bge-small-en-v1.5 (384-dim) | Dense vector embeddings | No external call; runs in Docker image | < 200 ms | None (local) |

**Note:** Exact model IDs are specified in `config/models.yaml` and can be updated without
a code deploy. The aliases above are the only names referenced in code.

---

## Local models

### BAAI/bge-small-en-v1.5

- **Purpose:** Semantic document and answer embeddings for pgvector HNSW retrieval.
- **Dimensions:** 384
- **Model file location (in Docker image):** `/app/.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5/`
- **Download:** Baked into image at build time via `HF_HUB_OFFLINE=1`; never fetched at runtime.
- **License:** MIT
- **Offline status:** `HF_HUB_OFFLINE=1` enforced — no outbound HuggingFace calls in production.

### Silero VAD (realtime-agent only)

- **Purpose:** Voice Activity Detection — frame-level speech / silence classification.
- **Location:** `/app/.cache/silero/` (realtime Docker image)
- **License:** MIT

### faster-whisper / Piper TTS (realtime-agent only)

- **Purpose:** Speech-to-text (STT) and text-to-speech (TTS) for the WebSocket realtime
  coaching loop.
- **Location:** Bundled in realtime-agent Docker image.
- **License:** Apache 2.0 (faster-whisper), MIT (Piper)

---

## External AI gateway

All calls to external LLM providers are routed through `packages/ai-gateway/praxis_ai_gateway/router.py`.
The gateway:
- Enforces `PromptBuilder` UNTRUSTED document isolation (no raw user input ever lands in a system prompt).
- Checks `zero_spend_mode=True` for worker jobs where user has not consented to LLM usage.
- Records routing decisions and latency in the `ai_call_log` table.
- Applies rate limits per `RoutingContext.user_id`.

Provider credentials are loaded from GCP Secret Manager — never from environment variables in
production. See `docs/SECURITY_MODEL.md`.

---

## Versioning and change control

1. Model aliases must not be changed without a code search and update of every `gateway.route("alias", ...)` call site.
2. New model IDs in `config/models.yaml` take effect on the next Cloud Run revision deployment.
3. Eval must be re-run (see `docs/AI_EVALUATION_REPORT.md`) before promoting a model change to production.
4. All model changes are tracked in the git history of `config/models.yaml`.

---

## BLOCKED

- Production model IDs: **BLOCKED** — requires GCP Secret Manager provisioning with actual
  provider API keys. Staging uses `config/models.yaml` values with dev keys.
