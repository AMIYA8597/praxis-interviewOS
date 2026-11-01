# PRAXIS InterviewOS — Phase 5 Known Limitations & Operational Constraints

**Document ID**: PROD-LIMITATIONS-001  
**Milestone**: Phase 5 — Production Engineering & Operational Constraints  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Engineering Transparency & Operational Limitations Register  

---

## 1. Documented Operational Constraints

In accordance with the 100% truthful engineering principle, this document records all verified runtime constraints, technical boundaries, and mitigation strategies for PRAXIS InterviewOS:

### 1. CPU-Bound Speech Recognition Sizing
- **Constraint**: The embedded faster-whisper speech recognition engine runs on quantized int8 models utilizing container CPU cores.
- **Measured Performance**: RTF is $0.185$ on 2 vCPU cores, providing responsive live transcription for up to 4 concurrent speech streams per container.
- **Mitigation / Growth Path**: For Enterprise Tier workloads ($> 500$ concurrent sessions), speech transcription can be decoupled into a dedicated GPU-backed GKE cluster utilizing NVIDIA L4 accelerators.

### 2. Cloud Run WebSocket Connection Duration Ceiling
- **Constraint**: Google Cloud Run enforces a maximum request timeout of 3600 seconds (60 minutes) for persistent WebSocket connections.
- **Impact**: Any interview practice session exceeding 60 continuous minutes will experience a connection termination by the load balancer.
- **Mitigation**: The desktop and web client applications implement automatic heartbeat-driven session renewal and state recovery. If a socket closes after 55 minutes, the client seamlessly establishes a new authenticated WebSocket connection without losing session context.

### 3. Database Connection Ceiling (Supabase Free/Pro Tier)
- **Constraint**: Standard Supabase PostgreSQL tiers impose a 100-connection limit.
- **Impact**: Unbounded connection pooling could crash the database during horizontal autoscaling.
- **Mitigation**: Strictly enforced configuration in `packages/config/settings.py` (`DB_POOL_SIZE = 2, DB_MAX_OVERFLOW = 3`). Peak demand across 10 API instances + 4 workers is mathematically capped at 64 connections, preserving a 36-connection buffer.

### 4. Client Audio Sample Format Requirement
- **Constraint**: The binary realtime wire protocol (`>BBIdI`) strictly expects 16-bit linear PCM audio sampled at 16,000 Hz mono.
- **Impact**: Raw 44.1 kHz or 48 kHz stereo audio submitted directly without conversion causes buffer decoding errors.
- **Mitigation**: The client-side audio pipeline in `apps/desktop` and `apps/web` resamples native hardware audio streams down to 16 kHz mono using the Web Audio API / WASAPI downsampler before framing into binary packets.

### 5. Third-Party LLM Provider Quotas & Rate Limits
- **Constraint**: In Bring-Your-Own-Key (BYOK) mode, candidates or organizations are subject to their own tier limits on OpenAI, Gemini, or DeepSeek.
- **Impact**: HTTP 429 Rate Limit exceptions from upstream providers.
- **Mitigation**: The AI Gateway's 3-state circuit breaker detects upstream 429s, automatically routes the turn request to secondary configured providers (or local Flan-T5), and notifies the candidate via a non-intrusive UI badge.
