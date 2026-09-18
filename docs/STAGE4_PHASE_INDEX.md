# PRAXIS — STAGE 4: FRONTEND / UI
## Complete Phase Index & Navigation Guide

> **This document is your quick reference for Stage 4's 17 phases.** The full detailed specification is in `PRAXIS_STAGE4_FRONTEND_UI_COMPLETE.md` — this index shows what each phase builds and the dependencies between them.

---

## STAGE 4 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│         PRAXIS FRONTEND (Stage 4)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  Electron Desktop    │      │  Next.js Web         │   │
│  │  (Practice Arena)    │      │  (Dashboard)         │   │
│  ├──────────────────────┤      ├──────────────────────┤   │
│  │ • Audio Capture      │      │ • Auth Pages         │   │
│  │ • Screen Capture     │      │ • Live Coaching HUD  │   │
│  │ • Study Workbench    │      │ • Candidate Profile  │   │
│  │ • Practice Sessions  │      │ • Session Review     │   │
│  │                      │      │ • Analytics          │   │
│  │                      │      │ • Admin Console      │   │
│  └──────────────────────┘      └──────────────────────┘   │
│           │                              │                 │
│           ▼                              ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │  @praxis/ui — Shared Component Library          │       │
│  │  (Button, Input, Card, MetricsDisplay, etc.)    │       │
│  └─────────────────────────────────────────────────┘       │
│           │                                                 │
└───────────┼─────────────────────────────────────────────────┘
            │
            ▼
  ┌──────────────────────────────────────────┐
  │   Backend (Stage 2) + AI Layer (Stage 3) │
  │   PostgreSQL (Stage 1)                   │
  └──────────────────────────────────────────┘
```

---

## PHASE BREAKDOWN

### **PHASE 4.0 — Verification & Frontend Environment**
- **What:** Verify backend connectivity, set up frontend dev tools
- **Dependencies:** Stages 1, 2, 3 running and tested
- **Produces:** 
  - `docs/CONNECTIVITY_CHECKLIST.md`
  - `scripts/doctor-frontend.ps1`
  - Root `package.json` with monorepo workspaces
  - TypeScript strict mode configured
  - `.env.local` populated with backend URLs
- **Gate:** Backend all connectable; linting and type-checking pass

---

### **PHASE 4.1 — Monorepo Structure & Build Tooling**
- **What:** Set up npm/pnpm workspaces, build pipeline, shared packages
- **Produces:**
  - Root workspace with `apps/` (desktop, web) and `packages/` (ui, types, config, schemas)
  - Vite config for Electron, Next.js config for web
  - `scripts/build-frontend.ps1` and `scripts/dev-frontend.ps1`
  - Pre-commit hooks (linting + type-checking)
- **Gate:** `npm run dev:desktop` and `npm run dev:web` both start; no TypeScript errors

---

### **PHASE 4.2 — Shared Component Package (@praxis/ui)**
- **What:** Build reusable React components (Button, Input, Card, Modal, Badge, Table, Spinner, Tabs, MetricsDisplay, TranscriptDisplay, CoachingFeedback, HintCard)
- **Why:** Both Electron and Next.js apps use the same components; single source of truth
- **Design Language:** Dark theme (near-black background #0a0a0a), restrained (not chat-app aesthetic), accessible (ARIA labels, keyboard nav)
- **Produces:**
  - `packages/ui/src/components/*.tsx` — all reusable components
  - `packages/ui/src/theme.ts` — design tokens (colors, typography)
  - Storybook for component preview and testing
  - Exports via `@praxis/ui` npm alias
- **Gate:** 
  - Storybook renders all components without errors
  - Unit tests pass (70%+ coverage)
  - All components have ARIA labels and dark-mode styling

---

### **PHASE 4.3 — Electron Main Process (Secure IPC & Storage)**
- **What:** The OS-level process that manages windows, IPC (inter-process communication), secure credential storage, global hotkeys
- **Critical:** Main process does NOT orchestrate AI; it only handles OS-level concerns
- **Produces:**
  - `src/main/index.ts` — app lifecycle, window creation, IPC routing
  - `src/main/storage.ts` — encrypted credential storage using `safeStorage`
  - Typed IPC channels (no raw string event names)
  - IPC handlers for storage, auth, session lifecycle
  - Security hardening: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`
  - Global hotkey registration (Ctrl+Shift+I to toggle interview)
- **Gate:**
  - Main process starts without errors
  - Credentials saved/retrieved via `safeStorage`
  - Context isolation enforced (verified in code)
  - Global hotkey registers and fires correctly

---

### **PHASE 4.4 — Electron Renderer: Audio Capture & VAD Visualization**
- **What:** Capture microphone audio, send to backend via WebSocket, visualize VAD state
- **Produces:**
  - `useAudioCapture()` hook — Web Audio API, 16-bit PCM capture, echo/noise cancellation
  - `useRealtimeSession()` hook — WebSocket connection to backend, event listeners
  - `float32ToPCM16()` converter — Float32 from Web Audio → PCM16 for backend
  - Audio frame header (seq + timestamp + length) for Phase 2's protocol
  - `VadVisualization.tsx` — real-time confidence bar
  - `AudioSettings.tsx` — microphone selection
- **Proves:** Real-time connection to backend; audio streaming working end-to-end
- **Gate:**
  - Audio captures via Web Audio API
  - WebSocket connects, sends auth token
  - Float32 → PCM16 conversion produces correct bytes
  - Frame header correctly structured
  - VAD visualization updates every ~250ms (proving backend is sending metrics)

---

### **PHASE 4.5 — Electron Renderer: Screen Capture & Diagram Tools**
- **What:** Capture screenshots, upload for OCR/vision processing (Phase 3.12), support diagram sketching
- **Produces:**
  - `useScreenCapture()` hook — native Screen Capture API integration
  - `useScreenshotUpload()` hook — POST screenshot to backend for processing
  - `DiagramCanvas.tsx` — simple drawing app for system design sketching
  - `useScreenshotHistory()` hook — localStorage-based screenshot archive
  - `StudyWorkbench.tsx` — full UI combining screenshot capture, upload, and hint display
- **Gate:**
  - Screen capture starts and prompts for permission
  - Screenshot uploads, backend returns problem type + hint ladder
  - Diagram canvas renders and allows drawing
  - Screenshot history tracked and queryable

---

### **PHASE 4.6 — Electron Renderer: Live Coaching HUD (250ms Proof)**
- **What:** Real-time coaching feedback display that updates every ~250ms, INDEPENDENT of LLM latency
- **Critical Design:** This is the visual proof that Stage 3's dual-path architecture (DSP metrics decoupled from LLM reasoning) is real
- **Produces:**
  - `CoachingHUD.tsx` — main coaching feedback component
  - Real-time update of metrics (WPM, filler rate, pause ratio, hedge count)
  - Transcript updates as they arrive from backend (interim + final)
  - Audio playback visualization
  - Coaching tips/feedback that appear as events arrive
  - Event-driven (WebSocket messages trigger immediate UI updates)
- **Timing Proof:** 
  - Metrics event every ~250ms
  - LLM reasoning happens asynchronously (doesn't block metrics)
  - User sees coaching updates in real-time even during slow question generation
- **Gate:**
  - Metrics display updates every ~250ms (measure with browser DevTools)
  - Coaching HUD remains responsive even during artificial 5s delay in LLM call
  - Transcript displays interim updates (partial transcription)
  - All visual updates < 100ms latency (browser rendering)

---

### **PHASE 4.7 — Electron Renderer: Practice Arena Session UI**
- **What:** The main Practice Arena interface — ties together audio capture, coaching HUD, transcript, and session controls
- **Produces:**
  - `PracticeArenaPage.tsx` — main session container
  - Session state: idle → warming up → ready → interviewer turn → awaiting answer → scoring → next turn
  - Start/Stop buttons
  - Difficulty selection (junior, mid, senior)
  - Session timer
  - Candidate name + target job display
  - Integration of:
    - `useAudioCapture()` + `useRealtimeSession()` (audio pipeline)
    - `CoachingHUD` (live coaching feedback)
    - `TranscriptDisplay` (streaming text)
    - Session metadata display
- **Gate:**
  - Session starts (WebSocket connects, audio captures)
  - State transitions correctly (ready → interviewer turn, etc.)
  - All components (audio, coaching, transcript) working together

---

### **PHASE 4.8 — Electron Preload & Context Isolation**
- **What:** The bridge between renderer (sandboxed React app) and main process (OS access)
- **Security:** Preload is the ONLY way renderer can access OS features; typed for safety
- **Produces:**
  - `src/preload/index.ts` — exposes only whitelisted IPC methods
  - TypeScript types for all exposed methods (e.g., `ipcInvoke<'storage:get'>`)
  - No direct Node.js access from renderer (no `require('fs')`, etc.)
- **Example:**
  ```typescript
  // preload/index.ts
  const api = {
    storage: {
      get: (key: string) => ipcInvoke('storage:get', key),
      save: (key: string, value: string) => ipcInvoke('storage:save', key, value)
    },
    session: {
      start: (id: string) => ipcSend('session:start', id)
    }
  };
  
  contextBridge.exposeInMainWorld('praxis', api);
  ```
- **Gate:**
  - `window.praxis` object exists with typed methods
  - Calling `window.praxis.storage.get()` works (no TypeErrors)
  - Attempting `require('fs')` from renderer throws error

---

### **PHASE 4.9 — Electron Window Management & Global Hotkeys**
- **What:** Manage multiple windows (main session, settings, debug), global hotkeys
- **Produces:**
  - Window lifecycle (create, restore, minimize, close)
  - Confirm-before-quit if session is active
  - Multiple windows with shared state (via IPC or global object)
  - Global hotkey Ctrl+Shift+S to start/stop recording
  - Global hotkey Ctrl+Shift+C to capture screenshot (even when window is unfocused)
  - Global hotkey Ctrl+Shift+I to toggle developer tools (dev mode only)
- **Gate:**
  - Multiple windows can be created and managed
  - Global hotkeys fire and trigger correct handlers
  - State is preserved across window lifecycle

---

### **PHASE 4.10 — Next.js Web App: Architecture & Auth**
- **What:** The web dashboard (analytics, candidate profile, session review, admin)
- **Architecture:** Next.js 15 App Router, Server Components by default, Client Components where needed
- **Produces:**
  - `apps/web/src/app/(auth)/` — login, signup, forgot-password pages
  - `apps/web/src/app/(dashboard)/` — protected routes (requires auth)
  - `apps/web/src/app/api/auth/` — auth endpoints (delegate to backend via API calls)
  - `useAuth()` hook — manages JWT token, auto-refresh, logout
- **Auth Flow:**
  1. User enters email + password on `/login`
  2. Frontend POSTs to backend `/auth/login` (Stage 2)
  3. Backend returns JWT token
  4. Frontend stores token in localStorage + cookie (httpOnly, Secure flags via backend)
  5. Subsequent requests include `Authorization: Bearer <token>`
- **Gate:**
  - Login page renders
  - Login works (posts to backend, receives token)
  - Protected routes redirect to login if no token
  - Token auto-refreshes before expiration

---

### **PHASE 4.11 — Next.js: Candidate Profile & Resume Management**
- **What:** View candidate's profile (skills, education, experience), upload/manage resumes
- **Produces:**
  - `/candidates/me` page — current user's profile
  - Profile sections: skills, education, work experience, projects
  - Resume upload (drag-drop or file picker)
  - Resume verification workflow (view extracted data, confirm or edit before marking verified)
  - Skills endorsement (candidate marks skills as verified)
- **Integration:**
  - Calls backend `/candidates/me` (GET profile)
  - Calls backend `/candidates/me/resumes` (POST upload, DELETE old versions)
  - Calls backend `/candidates/me/skills` (PATCH verify)
  - Reflects Stage 1's database schema: `candidates`, `candidate_resumes`, `candidate_skills`
- **Gate:**
  - Profile page loads and displays user data
  - Resume upload works (file transfers to backend)
  - Extracted resume data displayed for review
  - Skills can be marked as verified

---

### **PHASE 4.12 — Next.js: Session Review & Analytics**
- **What:** Review past sessions, see how you performed, track progress over time
- **Produces:**
  - `/sessions` page — list of past sessions (date, job, score, duration)
  - `/sessions/[sessionId]` page — detailed session review:
    - Full transcript (Q&A timeline)
    - Scoring breakdown (relevance, correctness, structure, grounding, specificity, conciseness)
    - Coaching feedback (extracted from turn_scores and feedback text)
    - Video/audio playback (if archived)
    - Weak areas flagged for study
  - `/analytics` page — aggregated stats:
    - Average score over time (trend chart)
    - Performance by domain (behavioral vs. technical vs. systems)
    - Most-asked topics (top 5 questions you've been asked)
    - Comparison: your score vs. prep-pack averages
- **Integration:**
  - Calls backend `/sessions` (list, with filters: job, date range)
  - Calls backend `/sessions/{sessionId}` (get full session with turns, scores, feedback)
  - Calls backend `/analytics/user-stats` (aggregated performance)
- **Gate:**
  - Sessions list loads and displays past interviews
  - Session detail page loads; transcript, scores, feedback all visible
  - Analytics page shows trend charts and performance comparisons

---

### **PHASE 4.13 — Next.js: Study Loop UI (Spaced Repetition)**
- **What:** Display study items (weak answers + screenshot problems), review with SM-2 scheduling
- **Produces:**
  - `/study` page — list of due study items
  - Study item card:
    - Original question or problem screenshot
    - Your prior answer (if applicable)
    - Difficulty indicator
    - "Review Now" button
  - Review modal:
    - Show question/problem
    - Prompt: "How would you answer this now?"
    - Text input or hint-ladder display (for screenshot problems)
    - Rating buttons: "Forgot" (0) → "Perfect" (5)
    - On submission, SM-2 scheduling updates next_review_at
  - Study analytics sidebar:
    - Total items: X
    - Due today: Y
    - Mastered: Z
- **Integration:**
  - Calls backend `/study-items` (list due items)
  - Calls backend `/study-items/{itemId}/review` (POST review with rating)
  - Backend returns updated next_review_at and ease_factor
- **Gate:**
  - Study items list loads and shows due items
  - Review flow works (submit rating, see feedback)
  - Study analytics updated after review

---

### **PHASE 4.14 — Next.js: Job Management & Prep Packs**
- **What:** Browse jobs, save favorites, review prep packs (15 pre-computed likely questions + resources)
- **Produces:**
  - `/jobs` page — job search/browse (with filters: company, role, seniority, tech stack)
  - `/jobs/[jobId]` page — job detail:
    - JD, required skills, seniority level
    - "Practice Interview for This Role" button
    - Prep pack: 15 likely questions grouped by topic
    - Resource links (company blog, engineering blog, recent news)
  - `/saved-jobs` page — bookmarked jobs for later
- **Integration:**
  - Calls backend `/jobs` (search, with filters)
  - Calls backend `/jobs/{jobId}` (get detail + prep pack)
  - Calls backend `/jobs/{jobId}/practice-session` (POST to start mock interview for this job)
- **Gate:**
  - Jobs list loads; can filter by role/company/seniority
  - Job detail loads; prep pack visible
  - "Practice Interview" button correctly starts a session scoped to this job

---

### **PHASE 4.15 — Next.js: Admin & Settings Console**
- **What:** Admin functionality (user management, session monitoring) + user settings (preferences, notification, storage)
- **Admin Features (if user is admin):**
  - User list (search, deactivate)
  - Session monitoring (list all sessions, see live transcripts if admin access is approved)
  - Analytics dashboard (aggregate performance across all users, optional)
  - Content management (manage jobs, interview questions — optional, can be deferred)
- **User Settings:**
  - `/settings/profile` — name, email, language preference
  - `/settings/preferences` — difficulty level (beginner → stress), interview duration, topics to focus on
  - `/settings/notifications` — email notifications on/off, frequency
  - `/settings/storage` — view storage usage, data retention policy, request data export/deletion
- **Produces:**
  - `/admin` page (admin-only, redirects if not admin)
  - `/settings/[section]` pages (profile, preferences, notifications, storage)
- **Gate:**
  - Non-admins cannot access `/admin` (redirected to `/settings`)
  - Admins can view user list and session logs
  - Settings changes persist (POST to backend `/settings`)

---

### **PHASE 4.16 — Testing, E2E, & Visual Regression**
- **What:** Test both Electron and Next.js apps end-to-end, verify visual consistency
- **Produces:**
  - Jest + React Testing Library for component unit tests (all components from Phase 4.2)
  - Playwright or Cypress for E2E tests:
    - E2E flow: Login → Start session → Answer question → Session ends → Review session
    - E2E flow: Login → Upload resume → Review extracted data → Mark verified
    - E2E flow: Login → Review study items → Submit rating → Next_review_at updates
  - Visual regression tests (Percy or similar) to detect unintended design changes
  - Electron integration tests (launch app, check window creation, test IPC)
- **Test Automation:**
  - Pre-commit hook runs unit tests
  - CI/CD runs full test suite (unit + E2E) on every commit
  - Visual regression run on design-file changes
- **Gate:**
  - All component unit tests pass (70%+ coverage)
  - E2E tests pass (3+ critical user flows)
  - No visual regressions detected
  - Electron app launches without errors

---

### **PHASE 4.17 — Stage 4 Completion Gate**
- **What:** Final checklist before Stage 4 is declared complete and the full system is ready for hackathon demo
- **Checklist:**
  - ✅ Monorepo builds (npm run build succeeds)
  - ✅ Electron app launches (npm run dev:desktop)
  - ✅ Next.js web app loads (npm run dev:web)
  - ✅ Shared components render and are accessible
  - ✅ Audio capture → WebSocket streaming works
  - ✅ Live coaching HUD updates every ~250ms (timing proof)
  - ✅ Session review shows past interviews with scores and feedback
  - ✅ Study loop displays due items and SM-2 scheduling works
  - ✅ All forms validate and submit correctly
  - ✅ Auth flow (login → token → protected routes) works
  - ✅ Full mock interview demo completes end-to-end without errors
  - ✅ Timing measurements documented (latency per component)
  - ✅ Code coverage 70%+ for critical paths
  - ✅ E2E tests pass
  - ✅ No console errors or warnings in normal use
- **Handoff:** The complete PRAXIS system (Stages 1–4) is ready for hackathon demo: backend running, frontend responsive, AI coaching working, all proven via real tests

---

## COPY-PASTE WORKFLOW

1. **Read this index** to understand Phase dependencies
2. **Start with Phase 4.0** (verify backend, set up environment)
3. **Follow phases in order** (4.0 → 4.1 → ... → 4.17)
4. **For each phase:**
   - Copy the detailed phase block from `PRAXIS_STAGE4_FRONTEND_UI_COMPLETE.md`
   - Paste into your coding agent
   - Execute all TASKS
   - Confirm every gate item with REAL evidence (test output, code, timing measurements)
   - Move to next phase only after all gates pass

---

## DOCUMENTATION REFERENCE

After Stage 4 is complete, update:
- `docs/FRONTEND_ARCHITECTURE.md` — component hierarchy, data flow, state management
- `docs/IPC_CONTRACT.md` — all typed IPC channels and their purposes
- `docs/ACCESSIBILITY_AUDIT.md` — WCAG compliance per component
- `docs/VERIFICATION_CHECKLIST.md` — add Stage 4 evidence section
- `docs/QUICK_START_DEVELOPER.md` — how to run Electron + Next.js locally for development

---

## KEY ARCHITECTURAL PRINCIPLES (enforced in Stage 4)

1. **Electron Main Process is a Thin Bridge**
   - No AI orchestration
   - No business logic
   - Only: window management, IPC routing, secure storage

2. **Context Isolation is Non-Negotiable**
   - `contextIsolation: true` in Electron config
   - Preload exposes only typed methods
   - Renderer cannot access Node.js APIs

3. **Live Coaching HUD Proves Dual-Path Architecture**
   - Metrics update every ~250ms
   - Independent of LLM latency
   - Visible proof in running demo

4. **Dark, Restrained Design Language**
   - Not a chat app
   - Dense, focused on information
   - Accessible (ARIA labels, keyboard nav, color contrast)

5. **Monorepo for Code Reuse**
   - `@praxis/ui` shared across Electron and Next.js
   - `@praxis/types` shared schemas
   - Single source of truth for design tokens

---

## NEXT STEPS

1. Download `PRAXIS_STAGE4_FRONTEND_UI_COMPLETE.md` (full detailed phases)
2. Start with Phase 4.0 in your coding agent
3. Follow the gates and confirm each phase
4. Once all 4 stages are complete, you have a production-grade hackathon project

**You've got this. 🚀**
