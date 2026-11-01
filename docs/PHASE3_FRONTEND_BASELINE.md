# PRAXIS InterviewOS — Phase 3 Frontend Baseline & Architecture Audit

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Base Commit**: `fd938b8e4ea3f54175c790571b241a8194ebfeba` (synchronized with `origin/main`)  
**Preserved Milestones**: `phase1-backend-db`, `phase2-ai-ml`  
**Date**: 2026-11-01  
**Status**: ACTIVE PRODUCTION IMPLEMENTATION  

---

## 1. Executive Summary

Phase 3 transitions PRAXIS InterviewOS from backend and AI/ML model certification into production web and desktop client applications.
The AI/ML intelligence engine developed in Phase 2—including real-time speech recognition (faster-whisper), 5-tier claim grounding, STAR rubric evaluation, and candidate-aware question synthesis—is surfaced to end-users via:
1. `apps/web`: Next.js 15 (App Router, React 19, TypeScript, Supabase SSR Auth).
2. `apps/desktop`: Electron 28+ (React 18, TypeScript, secure context-isolated preload, native audio loopback/mic capture).
3. `packages/ui`: Shared design system conforming to PRAXIS design tokens, accessible components, and WCAG 2.1 AA standards.
4. `packages/types`: Authoritative TypeScript integration contracts matching `docs/PHASE2_HANDOFF_PHASE3.md`.

---

## 2. Baseline Inventory & Repository Audit

### 2.1 Workspace Structure
| Path | Technology | Responsibility | Status |
| :--- | :--- | :--- | :--- |
| `apps/web` | Next.js 15, React 19, Tailwind CSS | Browser-based interview prep, onboarding, debrief, analytics, study plan | Functional; missing live session room |
| `apps/desktop` | Electron, React 18, TypeScript | High-performance practice arena with low-latency audio capture & Coaching HUD | Functional; 15 unit tests passing |
| `packages/ui` | React, TypeScript, Tailwind | Reusable accessible UI components (Button, Modal, CoachingFeedback, etc.) | 20 unit tests passing; needs 4 new components |
| `packages/types` | TypeScript | Shared cross-package data schemas and event contracts | Requires contract expansion |

### 2.2 Existing Routes in `apps/web`
- `/` — Landing page (placeholder; needs product presentation)
- `/auth` — Supabase authentication (login, registration)
- `/onboarding` — Initial candidate workflow and profile initialization
- `/(dashboard)/candidates` — Candidate profile, target roles, experience summary
- `/(dashboard)/platform/resume` — Resume upload, parsing status, extracted claims view
- `/(dashboard)/platform/tracker` — Application tracking and job matching
- `/(dashboard)/jobs/[id]` — Target job description analysis and skill requirements
- `/(dashboard)/sessions` — Session history, start practice modal
- `/(dashboard)/sessions/[id]/debrief` — Post-session evaluation, scoring breakdown
- `/(dashboard)/readiness` — PRAXIS Readiness Estimate display
- `/(dashboard)/study` — Adaptive spaced repetition and study modules
- `/(dashboard)/analytics` — Progress tracking over time
- `/(dashboard)/settings/providers` — Provider configuration and diagnostic settings
- `/(dashboard)/admin` — Administrative interface

### 2.3 Identified Implementation Gaps
1. **Live Practice Room Route Missing in Web**:
   While `apps/web/src/app/(dashboard)/sessions/[id]/debrief` exists, `sessions/[id]/page.tsx` was missing. Candidates need a full live interview room with preflight mic check, binary PCM16 streaming to WebSocket (`ws://<host>:8001/ws/sessions/{id}`), live transcription, and dual-path coaching feedback.
2. **Type Contract Incompleteness**:
   `packages/types/src/index.ts` only had basic metrics types. It must export all Phase 2 contracts: `ClaimClassification`, `MeasurementStatus`, `ClaimGrounding`, `EvaluationScore`, `ReadinessResponse`, and `RealtimeEventType`.
3. **Missing Specialized UI Components**:
   - `EvidenceReference`: Color-coded claim badge (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED, UNCERTAIN) with accordion source excerpt.
   - `ScoreDisplay`: 6-dimension evaluation breakdown with `measurement_status` awareness.
   - `ReadinessCard`: Calibrated readiness estimate with mandatory disclaimer and `INSUFFICIENT_EVIDENCE` fallback.
   - `AudioControl`: Device selection, input level meter, and live recording toggle.
4. **Landing Page Upgrade**:
   The root `/` route requires an authentic product marketing page showcasing interview prep workflows without misleading claims or fake guarantees.
5. **Debrief Page Integration**:
   The debrief page needs strict alignment with backend `/api/v1/sessions/{id}/debrief` schema, handling 5-tier claim badges and STAR structure.

---

## 3. Architecture & Security Invariants

1. **Zero Proctor Evasion (ADR-001)**:
   PRAXIS is an ethical interview preparation and coaching platform. No features for evading proctoring, hiding windows, or providing unauthorized assistance during assessments will ever be implemented or permitted.
2. **Strict Measurement Status Transparency**:
   Unmeasured scores must never be faked or displayed as 0 or 100%. If an evaluation service fails or is incomplete, `measurement_status` must reflect `ESTIMATED`, `DEGRADED`, or `UNAVAILABLE`, with scores rendered as `null` or explicit fallback states.
3. **Electron Security Isolation**:
   - `nodeIntegration: false`
   - `contextIsolation: true`
   - `sandbox: true`
   - Strict IPC channel allowlist via `preload/index.ts`
   - Content Security Policy (CSP) blocking unauthorized scripts.

---

## 4. Phase 3 Execution Roadmap

- **Stage 0**: Baseline audit, git verification, documentation initiation (this document).
- **Stage 1**: Foundation upgrades — `packages/types` expansion and `packages/ui` specialized components.
- **Stage 2**: Application shell, navigation, and auth flow hardening.
- **Stage 3**: Candidate profile, resume grounding, and job description experience.
- **Stage 4**: Dashboard, session orchestration, and preflight check.
- **Stage 5**: Web live interview room with binary audio WebSocket streaming.
- **Stage 6**: Debrief page, evidence citations, and PRAXIS Readiness Estimate.
- **Stage 7**: Adaptive study recommendations and spaced repetition integration.
- **Stage 8**: Desktop application hardening and audio capture loopback checks.
- **Stage 9**: Performance, responsive layouts, accessibility (WCAG 2.1 AA) validation.
- **Stage 10**: Integration certification, test suites pass, documentation suite completion.
