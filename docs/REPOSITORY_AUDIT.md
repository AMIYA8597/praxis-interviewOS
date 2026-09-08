# PRAXIS Repository Audit

**Date:** September 2026
**Target Directory:** `d:\work\interviewOS`

## Current State Summary
The repository currently contains the "InterviewOS Prime" MVP built sequentially across 9 phases. It successfully implemented the Next.js/Electron UI, the FastAPI backend, the Supabase schema, the realtime audio WebSocket (`MockTranscriber`), and extreme security/privacy boundaries. 

However, to comply with the new **PRAXIS** specification, several architectural migrations are required.

## Package Managers & Frameworks
- **Current**: pnpm workspace with `apps/web` (Next.js), `apps/desktop` (Electron), and `backend` (FastAPI via pip/uv).
- **Required**: The new spec mandates `realtime-agent/` as a distinct process and a robust `packages/` directory containing `ui/`, `types/`, `ai-gateway/`, and `config/`.

## Database Schema
- **Current**: Postgres 16 running via Docker with pgvector. The `alembic` migrations (`001`, `002`, `003`) define the full context graph, document_chunks, turn_metrics, and raw RLS policies.
- **Required**: No changes required to the schema logic, but `docker-compose.yml` must explicitly include Jaeger.

## Environment Variables
- **Current**: A basic `.env.example` exists.
- **Required**: Needs the exact segmented layout mandated in Task 5 (Core, Database, Redis, Local AI, Free-tier, BYO, Observability, Secrets) and pre-commit hook integration (e.g., `detect-secrets`).

## Working Functionality
- The candidate graph mapping, Magic Byte validation, SSRF intercepts, Prompt Injection fencing (`PromptBuilder`), and strictly decoupled `docs/REALTIME.md` pure-DSP models are fully operational.

## Path Forward
We will proceed to Task 2 (Toolchain Doctor) and then execute Task 3 to extract `realtime-agent` and `ai-gateway` into their proper boundaries.
