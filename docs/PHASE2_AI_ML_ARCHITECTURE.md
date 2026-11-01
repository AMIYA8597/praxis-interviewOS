# PRAXIS InterviewOS — Phase 2 AI/ML Target Architecture

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Phase**: Phase 2 — AI/ML Intelligence  
**Classification**: COMPLETE SYSTEM ARCHITECTURE SPECIFICATION  

---

## 1. System Architecture Overview

PRAXIS InterviewOS combines realtime multimodal speech processing, candidate background retrieval, adaptive question generation, and evidence-grounded evaluation into a coordinated distributed platform:

```mermaid
flowchart TD
    subgraph ClientLayer["Client Layer (Web & Desktop)"]
        WSClient[Realtime WebSocket Client]
        Mic[Microphone PCM16 Audio Stream]
        HUD[Realtime Coaching HUD]
    end

    subgraph AudioPipeline["Real-Time Audio Pipeline"]
        FrameParser[Binary Frame Parser: >BBIdI Header]
        VAD[Silero VAD ONNX]
        STTRouter[STT Router: faster-whisper 2 vCPU / Cloud STT]
        TTS[Piper TTS ONNX: en_US-lessac-low]
    end

    subgraph Orchestration["Realtime Agent Orchestrator"]
        FastPath[Fast Path: Cadence, WPM, Filler, VAD]
        SlowPath[Slow Path: Policy Engine, Scoring, RAG]
        StateMachine[Session State Machine & Redis Recovery]
    end

    subgraph AIGateway["AI Gateway (Unified Boundary)"]
        Router[Task Router & Fallback Chain]
        Budget[Budget Guard & Consent Tracker]
        Safety[Prompt Injection & Output Safety Validator]
        CircuitBreakers[Circuit Breakers & Retries]
    end

    subgraph DataAndKnowledge["Database & Knowledge Base (PostgreSQL / Supabase)"]
        Chunks[document_chunks: pgvector HNSW + tsvector GIN]
        TenantRLS[FORCE Row Level Security]
        SessionStore[practice_sessions, session_turns, session_claims]
    end

    Mic -->|18-byte frames| FrameParser
    FrameParser --> VAD
    VAD --> STTRouter
    STTRouter --> Orchestration
    FastPath -->|~1Hz coaching.metrics| HUD
    SlowPath --> AIGateway
    AIGateway --> Chunks
    AIGateway --> SessionStore
    SlowPath --> TTS
    TTS --> WSClient
```

---

## 2. Core Architectural Pillars

### 2.1 Audio Ingestion & Realtime Protocol
- Strict 18-byte big endian header (`>BBIdI`).
- Raw 16kHz mono 16-bit PCM streaming.
- Non-blocking fast path (< 10ms latency) for cadence and WPM delivery independent of slow-path LLM latency.

### 2.2 Candidate Context & Hybrid RAG
- Dual-channel retrieval combining `pgvector` HNSW cosine similarity (dense) and PostgreSQL `tsvector` BM25 (sparse lexical).
- Reciprocal Rank Fusion (RRF) with rank constant $k=60$.
- Strict cross-tenant isolation enforced by PostgreSQL RLS.

### 2.3 Evidence-Grounded Claim Verification
- 5-tier classification: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`.
- No unverified claim silently becomes supported.
- Exact source chunk provenance and excerpt tracking.

### 2.4 Multimodal Rubric Scoring
- Normalized continuous scoring $[0.0, 1.0]$ across Correctness, Relevance, Structure, Specificity, Grounding, Conciseness.
- Missing measurements stored as `null` with `measurement_status="UNAVAILABLE"`, never fabricated zeros.
- Specialized rubrics for Coding (sandbox execution), System Design (24-step flow), and Behavioral (STAR methodology).

### 2.5 Gateway Boundary Integrity
- Zero direct provider SDK imports outside `packages/ai-gateway`.
- Automatic fallback chain across local and cloud providers.
- Hard zero-spend blocking and user consent validation.
