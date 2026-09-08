PART 3 — FREE-FIRST TOOL MAP AND VERIFICATION PROTOCOL

3.1 The hierarchy
   LOCAL / OPEN SOURCE          ← default, always available, zero cost, zero quota
            ↓
   FREE CLOUD TIER              ← used when configured and within quota
            ↓
   USER'S OWN API KEY (BYO)     ← used when configured and budget allows
            ↓
   PAID (never automatic)       ← requires explicit per-provider opt-in

The application must never make a billable call without the user having explicitly enabled that provider and acknowledged a cost warning. Implement ZERO_SPEND_MODE=true as the shipped default.

3.2 The stack

Status of this table: compiled from knowledge current to May 2026. Free-tier terms, rate limits, and model catalogs change frequently and without notice. Phase 0 requires the agent to re-verify every row against official documentation before implementation, and to record the verification date in docs/TOOL_VERIFICATION.md. Treat any row here as a hypothesis, not a fact.

| Layer | Primary (free/local) | Free cloud tier | BYO / upgrade | Notes & caveats |
|-------|----------------------|-----------------|---------------|-----------------|
| Database | Postgres 16 in Docker | Supabase Free | Supabase Pro | Free tier includes Postgres, Auth, Storage, RLS, and pgvector. Historically ~500 MB DB / ~1 GB storage / ~50k MAU, with project pausing after ~7 days of inactivity — this bites during a hackathon weekend. Add a keepalive cron and a documented un-pause procedure. Verify current limits at supabase.com/pricing. |
| Vector search | pgvector in the same Postgres | same | Qdrant/Weaviate later | Do not add a separate vector DB. HNSW index on document_chunks.embedding. |
| Embeddings | bge-small-en-v1.5 (384-dim) via sentence-transformers, CPU, ~30 MB | Gemini embedding API free tier | OpenAI text-embedding-3-small | Local is genuinely good enough for resume/JD retrieval and eliminates a network hop. Store embedding_model + embedding_version on every row so you can re-index. |
| STT (realtime) | faster-whisper (CTranslate2), small.en or distil-large-v3, CPU-viable, GPU-fast | Groq Whisper — very fast, generous free tier historically; Deepgram free credit; AssemblyAI free tier | OpenAI / Gemini realtime | Local is the default. Ship a hardware detector that picks model size from RAM/VRAM. Never fake a transcript — if local STT is too slow on the machine, say so and name the fix. |
| VAD | Silero VAD (ONNX, ~1 MB, ~1 ms/frame CPU) | — | — | Local only. This is in the barge-in hot path; a network call here would be an architectural error. |
| TTS (AI interviewer voice) | Piper (ONNX, local, fast, offline) | Edge-TTS wrapper; provider TTS free tiers | OpenAI/ElevenLabs | Piper is the right default: offline, no quota, low latency, and supports voice selection. Must support instant stop for barge-in — verify the streaming API can be cancelled mid-utterance. |
| LLM — fast path (classification, turn-end, filler detection) | Ollama + qwen2.5:3b / llama3.2:3b | Groq (very fast inference, free tier); Cerebras free tier | any | The fast path must never hit a slow provider. Budget < 200 ms. |
| LLM — reasoning path (scoring, follow-up planning, feedback) | Ollama + qwen2.5:14b if hardware allows | Google Gemini free tier (AI Studio key); Groq larger models; OpenRouter free-tier models | OpenAI / Anthropic / DeepSeek / xAI | Gemini's free AI Studio tier has historically been the most generous for this use case. Verify current RPM/TPD limits. |
| Vision (screenshot solving) | PaddleOCR or Tesseract 5 + local VLM (moondream, qwen2-vl:7b via Ollama) | Gemini vision free tier | OpenAI / Claude / Grok vision | Hybrid pipeline: OCR first; only escalate to a VLM when OCR confidence is low or the image is a diagram. This halves latency and cost. |
| Cache / queue / session | Redis in Docker | Upstash Redis free tier | managed Redis | Local Redis for dev. Upstash if you need the demo hosted. |
| Job queue | arq (asyncio-native, Redis-backed) | — | — | Lighter than Celery, async-native, correct choice for a FastAPI codebase. Do not use Kafka. |
| Auth | Supabase Auth | same | same | Email/password + magic link + optional GitHub OAuth. Do not hand-roll password hashing. |
| Object storage | Local filesystem (dev) | Supabase Storage | S3-compatible | Abstract behind an ObjectStorage protocol from day one. |
| Web hosting | local | Vercel Hobby | Vercel Pro | Hobby is non-commercial only per Vercel's terms. Fine for a hackathon/portfolio; flag it in DEPLOYMENT.md and budget $20/mo the moment it becomes commercial. |
| API hosting | local / Docker | Render or Fly.io free allowances | any container host | The backend needs long-running WebSocket connections and a background worker — verify the chosen tier permits both and check cold-start behavior. Serverless functions are wrong for the realtime agent. |
| Telemetry | OpenTelemetry SDK + local Jaeger in Docker | Grafana Cloud free; Honeycomb free | any | Local Jaeger is enough and demos beautifully. |
| Error tracking | console + structured logs | Sentry free tier | Sentry paid | Scrub PII before send. |
| CI/CD | — | GitHub Actions free minutes on public repos | — | Public repo = generous free minutes, and a public repo is itself a portfolio asset. |
| Code sandbox | Docker container, no network, non-root, ro-rootfs, rlimits | — | Firecracker/gVisor later | Only needed if you enable code execution in the Study Workbench. Off by default. |
| Desktop shell | Electron (latest stable at build time) | — | — | Verify the current version at build time; do not pin to a version named in this document. |
| Installer | electron-builder → NSIS .exe | — | code-signing cert (~$100–400/yr) | Unsigned builds trigger SmartScreen on Windows 11. Document this honestly rather than pretending. |

3.3 The verification protocol (mandatory)

Before any phase that integrates an external service, the agent must:

1. Fetch the current official documentation for that service.
2. Record in docs/TOOL_VERIFICATION.md: service, URL, date checked, current free-tier limits, current model IDs, current endpoint shape, and any deprecation notices.
3. If reality diverges from this document, follow reality and note the divergence. This document is not authoritative over the vendor's docs.
4. Never hardcode a model ID in business logic. Model IDs live in config/models.yaml, referenced by alias.

A literal `<VERIFY_AT_BUILD>` left in the file must fail the startup validator with a clear message. This is deliberate: it forces the verification step instead of letting a stale ID ship.
