# PRAXIS System Architecture

## Overview
PRAXIS is split into three primary deployment bounds:
1. **Frontend (Next.js / Electron)**: Handles UI, hardware capture (Desktop), and settings.
2. **Core Backend (FastAPI)**: Manages Postgres state, the AI Gateway (routing/budgets), the Hybrid RAG engine, and all REST endpoints.
3. **Realtime Agent (FastAPI / WebSockets)**: A decoupled service dedicated to low-latency binary multiplexing, pure-DSP audio metrics (VAD), and streaming TTS.

## AI Gateway
The core backend exposes an internal SDK wrapper that enforces Cost Budgets (`ZERO_SPEND_MODE`) and circuit breakers. No business logic file is allowed to import `openai` directly.

## Hybrid RAG
Candidate facts are extracted via `arq` background workers and stored in `pgvector`. At retrieval time, we enforce a hard SQL `WHERE verified_by_user = true` constraint, ensuring the LLM never hallucinates candidate metrics during a mock interview.
