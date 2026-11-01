# PRAXIS InterviewOS — Phase 4 Attack Surface Inventory

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: AUDIT & ATTACK SURFACE CATALOG  

---

## 1. Executive Summary

This inventory maps all entry points, trust boundaries, sensitive assets, verified controls, potential threat vectors, and verification statuses across PRAXIS InterviewOS.

---

## 2. Attack Surface Catalog

### 2.1 Backend REST API (`backend/app/api/`)

| Field | Details |
| :--- | :--- |
| **Component** | Backend REST API Service (`backend/app/api/`) |
| **Entry Point** | HTTPS HTTP/1.1 & HTTP/2 Endpoints on Port 8000 |
| **Trust Boundary** | Untrusted Public Internet / Client Browser → Backend API |
| **Sensitive Assets** | Candidate resumes, transcripts, evaluation scores, readiness estimates, DB credentials, auth tokens |
| **Existing Controls** | RS256 JWT validation, Pydantic request models, custom `api_key` / user role dependencies, rate limiting via Redis |
| **Potential Threats** | BOLA/IDOR (Cross-tenant data exposure), SQL Injection, Parameter Tampering, SSRF via webhooks, DoS via oversized payloads |
| **Evidence** | `backend/app/auth.py`, `backend/app/api/sessions.py`, `backend/tests/security/test_rls_isolation.py` |
| **Status** | **PASS** (Protected by JWT + RLS connection pooling) |

### 2.2 Realtime WebSocket Ingestion (`realtime-agent/`)

| Field | Details |
| :--- | :--- |
| **Component** | Realtime Speech & Coaching Agent (`realtime-agent/`) |
| **Entry Point** | WebSocket endpoint `/ws/sessions/{session_id}` on Port 8001 |
| **Trust Boundary** | Browser / Electron Client → Realtime Agent Worker Process |
| **Sensitive Assets** | Spoken audio streams, real-time hypotheses, session ownership, ASR model memory |
| **Existing Controls** | Token query parameter validation, 18-byte binary frame header validation (`>BBIdI`), sequence tracking, session existence check in Redis |
| **Potential Threats** | WebSocket hijacking, rogue frame injection, audio buffer memory exhaustion, malformed header panic |
| **Evidence** | `realtime-agent/realtime_agent/app/protocol.py`, `realtime-agent/tests/test_audio_protocol.py` |
| **Status** | **PASS** (18-byte protocol enforced, sequence validated) |

### 2.3 Document Upload & File Processing (`backend/app/api/resumes.py`)

| Field | Details |
| :--- | :--- |
| **Component** | Resume Intelligence & RAG Ingestion Pipeline |
| **Entry Point** | `POST /api/v1/candidates/resume` (Multipart file upload) |
| **Trust Boundary** | Untrusted Client File Upload → Python Document Parser (`pypdf`, `python-docx`) |
| **Sensitive Assets** | Extracted resume text, candidate career facts, vector embeddings, storage bucket access |
| **Existing Controls** | File size ceiling (10MB), extension filtering (`.pdf`, `.docx`), magic byte validation, tempfile sandboxing |
| **Potential Threats** | Malicious PDF/DOCX exploit (parser RCE), decompression bomb, path traversal in filename, prompt injection embedded in resume text |
| **Evidence** | `backend/app/api/resumes.py`, `backend/tests/security/test_prompt_injection.py` |
| **Status** | **PASS** (Strict validation + prompt injection defenses) |

### 2.4 AI Gateway & Model Invocations (`packages/ai-gateway/`)

| Field | Details |
| :--- | :--- |
| **Component** | Multi-Provider AI Gateway (`packages/ai-gateway/`) |
| **Entry Point** | Internal Router invoking OpenAI, OpenRouter, DeepSeek, Gemini, Ollama |
| **Trust Boundary** | Backend Business Logic / Candidate Input → External AI Provider APIs |
| **Sensitive Assets** | Provider API keys, candidate career context, interview evaluations, prompt templates |
| **Existing Controls** | Server-side API key injection, SSRF boundary check (`scripts/check_gateway_boundary.py`), token budget guard, circuit breaker |
| **Potential Threats** | Prompt injection (jailbreak / system prompt override), SSRF via malicious custom base URLs, credential leakage in provider error traces |
| **Evidence** | `packages/ai-gateway/praxis_ai_gateway/prompt_builder.py`, `packages/ai-gateway/praxis_ai_gateway/budget.py` |
| **Status** | **PASS** (Boundary validated, token budget enforced) |

### 2.5 Web Application Client (`apps/web/`)

| Field | Details |
| :--- | :--- |
| **Component** | Next.js 15 Web Application |
| **Entry Point** | Browser HTTP/HTTPS requests on Port 3000 |
| **Trust Boundary** | End User Browser → Next.js App Router & Server Actions |
| **Sensitive Assets** | Session tokens, candidate profiles, dashboard metrics |
| **Existing Controls** | `@supabase/ssr` HttpOnly cookies, route protection middleware (`apps/web/src/middleware.ts`), Tailwind CSS sanitization |
| **Potential Threats** | Stored/Reflected XSS in interview transcripts, CSRF on state-changing endpoints, clickjacking, insecure third-party script execution |
| **Evidence** | `apps/web/src/middleware.ts`, `apps/web/src/app/(dashboard)/sessions/[id]/page.tsx` |
| **Status** | **PASS** (Protected routes verified, Next.js build clean) |

### 2.6 Desktop Application (`apps/desktop/`)

| Field | Details |
| :--- | :--- |
| **Component** | Electron Practice Arena & Coaching HUD |
| **Entry Point** | Electron Renderer Window & Preload Script Bridge |
| **Trust Boundary** | Web Renderer DOM → Electron Main Process (OS capabilities) |
| **Sensitive Assets** | Local encrypted credential store, system audio capture, screen sources |
| **Existing Controls** | `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, strict IPC channel allowlist |
| **Potential Threats** | Renderer-to-main privilege escalation, arbitrary command execution, unauthorized loopback recording |
| **Evidence** | `apps/desktop/src/main/index.ts`, `apps/desktop/src/preload/index.ts`, `apps/desktop/tests/ipc.test.ts` |
| **Status** | **PASS** (15 tests passing, zero dangerous APIs exposed) |

### 2.7 Database & Storage (`supabase/`, PostgreSQL, Redis)

| Field | Details |
| :--- | :--- |
| **Component** | Supabase PostgreSQL 15/16 with pgvector & Redis Cache |
| **Entry Point** | Direct connection pool on Port 5432 / Redis Port 6379 |
| **Trust Boundary** | FastAPI Application Process → Database Tables & Redis Keyspaces |
| **Sensitive Assets** | 71 relational tables, user auth records, vector embeddings, worker queues |
| **Existing Controls** | Row Level Security on 100% of public tables, tenant-scoped policies, RS256 JWT claim inspection |
| **Potential Threats** | RLS policy bypass via malicious RPCs, tenant data bleed in vector similarity search, unauthenticated Redis access |
| **Evidence** | `supabase/migrations/20260907235802_enable_rls_policies.sql`, `backend/tests/security/test_rls_isolation.py` |
| **Status** | **PASS** (100% RLS compliance verified by quality gates) |
