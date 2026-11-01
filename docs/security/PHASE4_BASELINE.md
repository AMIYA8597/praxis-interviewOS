# PRAXIS InterviewOS — Phase 4 Security Baseline & Starting Condition

**Milestone**: Phase 4 — Enterprise Security Engineering & Production Security Certification  
**Target Branch**: `phase4-security`  
**Base Commit SHA**: `f2ace3a` (`feat(phase3): deliver production web & desktop clients, shared design system, and realtime interview room`)  
**Base Golden Branch**: `main` (synchronized with `origin/main` at `f2ace3a`)  
**Preserved Milestones**: `phase1-backend-db`, `phase2-ai-ml`, `phase3-web-desktop` (all preserved locally and remotely)  
**Date**: 2026-11-01  
**Status**: ACTIVE SECURITY AUDIT & ENGINEERING  

---

## 1. Executive Baseline & Environment

This document records the authoritative starting state of the PRAXIS InterviewOS repository at the commencement of Phase 4.

### 1.1 Git Topology
- **Current Branch**: `phase4-security` (branched from `main` @ `f2ace3a`).
- **Working Tree**: Clean (`git status --short` clean).
- **Remote Synchronization**:
  - `main` matches `origin/main` @ `f2ace3a`.
  - `phase3-web-desktop` matches `origin/phase3-web-desktop` @ `f2ace3a`.
  - `phase2-ai-ml` matches `origin/phase2-ai-ml` @ `fd938b8`.
  - `phase1-backend-db` matches `origin/phase1-backend-db` @ `47de49f`.
  - All 5 obsolete historical branches have been pruned locally and remotely.

### 1.2 Monorepo Components & Scope
| Workspace Path | Technology Stack | Security Role / Attack Surface | Baseline Status |
| :--- | :--- | :--- | :--- |
| `apps/web` | Next.js 15, React 19, Tailwind, Supabase SSR | Browser attack surface, CSRF, XSS, SSRF via server actions, auth cookies | Functional, 16 routes build cleanly |
| `apps/desktop` | Electron 28+, React 18, Native Audio | Renderer privilege escalation, IPC safety, safe storage, audio capture | Functional, 15 tests pass, `tsc` clean |
| `backend/app` | FastAPI, Python 3.11+, SQLAlchemy, Asyncpg | API routes, JWT validation, RLS connection pooling, rate limiting | Functional, 75/75 capabilities pass |
| `realtime-agent`| Python, WebSocket, faster-whisper, WebRTC/VAD | Binary audio streaming (`>BBIdI`), frame validation, session hijacking | Functional, 35 tests pass |
| `packages/ai-gateway`| Python, httpx, LiteLLM / Provider adapters | Prompt injection, credential leakage, SSRF on custom base URLs | Functional, 22 tests pass |
| `packages/ui` | React, TypeScript, Tailwind | Design system, XSS in transcript/claim rendering, WCAG 2.1 AA | Functional, 28 tests pass |
| `packages/types` | TypeScript | Authoritative cross-tier schema definitions | Clean source export |
| `supabase/` | PostgreSQL 15/16, pgvector, RLS | 71 relational tables, 31 migrations, tenant isolation, RLS policies | 100% tables have RLS policies |

---

## 2. Baseline Test & Gate Execution Results

Prior to Phase 4 code modifications, the following baseline verification checks were executed and confirmed green:

| Gate / Suite | Command | Result | Verification Details |
| :--- | :--- | :--- | :--- |
| **Final Quality Gate** | `python scripts/final_quality_gate.py` | **15/15 PASS** | RLS on all tables, no hardcoded secrets, ruff clean |
| **Backend Completeness Gate** | `python scripts/check_backend_completeness.py` | **75/75 PASS** | All required security, AI, API, and worker modules present |
| **Shared UI Component Tests** | `pnpm --filter @praxis/ui test` | **28/28 PASS** | 14 suites, in-band execution |
| **Desktop Tests** | `pnpm --filter desktop test` | **15/15 PASS** | 11 suites, IPC, audio frame streaming, Coaching HUD |
| **Desktop Build** | `pnpm build:desktop` | **PASS** | `tsc` exit code 0 |
| **Web Production Build** | `pnpm build:web` | **PASS** | Next.js 15.3.3 compiled 16 routes, 102 kB shared JS |

---

## 3. Existing Security Invariants & Policies
1. **ADR-001 Zero Proctor Evasion Invariant**:
   PRAXIS is an ethical interview coaching and practice platform. It contains zero mechanisms for proctor evasion, window hiding, clandestine overlays, or live assessment cheating.
2. **Strict RLS Isolation**:
   All 71 public database tables have Row Level Security enabled.
3. **No Mocked Metrics / Data Integrity**:
   Unmeasured metrics must remain `null` with explicit `measurement_status` (`MEASURED`, `ESTIMATED`, `DEGRADED`, `UNAVAILABLE`).
4. **Service Role Key Isolation**:
   Supabase service role keys must never be exposed to frontend code or client bundles.

---

## 4. Phase 4 Objectives & Methodology
Phase 4 follows an evidence-based, 11-stage security engineering lifecycle:
1. Attack Surface Inventory & Baseline
2. Threat Modeling & Trust Boundaries (STRIDE)
3. Authentication & Multi-Tenant Authorization Hardening
4. API & Web Application Security (XSS, CSRF, CSP, CORS)
5. Realtime WebSocket & Audio Ingestion Security
6. AI, RAG, Prompt Injection & Provider Security
7. Coding Sandbox & Electron Desktop Privilege Boundary
8. Secrets Management & Cloud Infrastructure (GCP / Terraform)
9. Privacy, Retention & Deletion Cascades
10. CI/CD Automated Security Gates
11. Final Evidence Collection & Phase 5 Handoff
