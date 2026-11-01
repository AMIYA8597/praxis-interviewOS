# PRAXIS InterviewOS — Phase 3 Web Application Implementation

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: APPLICATION IMPLEMENTATION SPECIFICATION  

---

## 1. Overview & Technology Stack

The web application (`apps/web`) is built with:
- **Framework**: Next.js 15 (App Router, Turbopack compatible).
- **Core Libraries**: React 19, TypeScript 5, Tailwind CSS.
- **State & Data**: Deterministic API clients with custom fetch wrappers, React hooks.
- **Audio & Media**: Web Audio API (16kHz mono sampling, PCM16 conversion, ScriptProcessor/AudioWorklet).
- **Authentication**: `@supabase/ssr` with Next.js route middleware.

---

## 2. Route Directory & Functional Matrix

| Route | Rendering Mode | Description |
| :--- | :--- | :--- |
| `/` | Static | Marketing & product landing page outlining speech intelligence and evidence grounding |
| `/auth` | Static | Login and registration portal with email/password authentication |
| `/onboarding` | Static | Initial candidate profile setup and experience level capture |
| `/(dashboard)/candidates` | Static/Client | Profile management, target roles, experience summary |
| `/(dashboard)/platform/resume` | Static/Client | Resume document upload, background parsing status, claim extractor |
| `/(dashboard)/platform/tracker` | Static/Client | Job application tracker and target company alignments |
| `/(dashboard)/jobs/[id]` | Dynamic | Target job description analysis and skill requirement mapping |
| `/(dashboard)/sessions` | Static/Client | Practice session list, status badges, start practice modal |
| `/(dashboard)/sessions/[id]` | Dynamic/Client | **Live Practice Arena**: Audio streaming, live transcripts, Coaching HUD |
| `/(dashboard)/sessions/[id]/debrief` | Dynamic/Client | **Debrief & Evaluation**: ScoreDisplay, 5-tier EvidenceReference, STAR breakdown |
| `/(dashboard)/readiness` | Static/Client | PRAXIS Readiness Estimate card, predictive indicators, adaptive plan |
| `/(dashboard)/study` | Static/Client | SuperMemo SM-2 spaced repetition cards generated from weak answers |
| `/(dashboard)/analytics` | Static/Client | Longitudinal trend analysis across completed sessions |
| `/(dashboard)/settings/providers` | Static/Client | AI Provider credentials and diagnostic health indicators |
| `/(dashboard)/admin` | Static/Client | Administrative inspection controls |

---

## 3. Production Build Certification

```bash
pnpm --filter web run build
```
- Next.js 15.3.3 optimized production build:
  - 16 static and dynamic routes compiled successfully.
  - Zero TypeScript errors (`tsc --noEmit` clean).
  - First Load JS shared by all routes: **102 kB**.
  - Route bundles: all under 5 kB individual payload.
