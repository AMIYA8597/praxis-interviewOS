# Project: PRAXIS — Realtime AI Interview Coaching Platform

**Summary:** 
Full-stack, production-structured platform that runs live, voice-driven mock interviews with sub-second turn-taking and barge-in. It grounds every question and every piece of feedback in a human-reviewed candidate knowledge graph and a JD-derived blueprint. Closes the loop with measured delivery analytics and a spaced-repetition study plan. Architected free-first across five interchangeable AI providers with automatic failover.

### What I built:
- **A realtime audio pipeline** (VAD, streaming STT, barge-in cancellation, turn detection) with a measured, displayed, sub-250ms end-to-end latency budget, instrumented with OpenTelemetry.
- **A provider-agnostic AI gateway** — the only place any model SDK is imported — with a capability registry, circuit breakers, and automatic failover across local (Ollama), free-tier (Groq, Gemini), and optional paid providers, defaulting to zero spend.
- **A human-in-the-loop candidate knowledge graph** where every fact used as interview evidence is explicitly reviewed and confirmed, with full claim-to-source provenance surfaced in the UI.
- **A dual-path realtime architecture** separating a sub-300ms pure-DSP coaching-metrics path from the LLM reasoning path, so live feedback never blocks on model latency.
- **A follow-up memory graph and claim-consistency engine** that keeps a multi-turn conversation coherent and flags a candidate's own contradictions for later review.
- **A hint-ladder multimodal problem solver** (OCR-first, VLM-escalation) for coding/SQL/system-design/ML study, deliberately designed to teach rather than answer.
- **Full RLS-secured multi-tenant Postgres schema** on Supabase's free tier, with an automated cross-tenant isolation test in CI.
- **A documented, deliberate scope decision** (coaching vs. live-interview assistance) with the reasoning captured as an ADR.

### Stack
**Electron + React/TypeScript** (desktop), **Next.js 15 App Router** (web dashboard), **Python/FastAPI** (core API + separate realtime agent process), **Supabase** (Postgres, pgvector, Auth, Storage, RLS), **Redis + arq**, **faster-whisper**, **Silero VAD**, **Piper TTS**, **Ollama**, **Groq**, **Google Gemini**, **OpenTelemetry**.
