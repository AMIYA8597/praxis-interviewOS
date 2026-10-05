# PRAXIS (InterviewOS)

[![CI Status](https://github.com/AMIYA8597/praxis-interviewOS/actions/workflows/ci.yml/badge.svg)](https://github.com/AMIYA8597/praxis-interviewOS/actions)

A realtime, multimodal AI interview coaching & candidate intelligence platform.

PRAXIS is a massive, multi-process application designed to simulate live technical interviews. It enforces a strict separation of concerns, decoupling the stateless REST core from the low-latency stateful WebSocket engine, and separates the Next.js web dashboard from the Electron desktop practice arena.

---

## CI Enforcement & Security Guarantees
Our CI pipeline (`.github/workflows/ci.yml`) strictly enforces architectural and security boundaries on every commit:
- **Defense-in-Depth RLS:** Asserts that every single tenant-scoped table has `FORCE ROW LEVEL SECURITY` natively enabled.
- **Path Traversal Security:** Runs isolation tests to prevent any storage paths from escaping the `/resumes/` boundary.
- **Root Graveyard Guard:** Checks the root directory for orphaned/loose `.py` scratch scripts and halts the build if any are found, enforcing strict folder hygiene.
- **Idempotency Checks:** Evaluates `scripts/migrate.py` cross-checking the `schema_migrations` tracking table.

---

## 🏗️ Directory Structure & Architecture

```text
praxis/
├── apps/
│   ├── desktop/            # Electron App (React + Vite) - Live Practice Arena (System Audio/Screen Capture)
│   └── web/                # Next.js 15 App - Dashboard, Analytics, Job Tracker, Settings
├── backend/                # Python (FastAPI + ARQ) - Core REST API & Background Workers
├── packages/
│   ├── ai-gateway/         # PRAXIS AI Gateway - LLM routing, prompting, scoring, claims grounding
│   ├── config/             # Shared TypeScript configurations (ESLint, TSConfig)
│   ├── types/              # Shared TypeScript definitions (IPC channels, API contracts)
│   └── ui/                 # Shared React Component Library (Tailwind, Storybook)
├── realtime-agent/         # Python (FastAPI WebSockets) - VAD, Turn Detection, Audio Streaming
├── scripts/                # Utility scripts (RLS generators, doctor checks)
└── supabase/               # Postgres schema, Row-Level Security policies, and Storage buckets
```

The application is completely remediated and stabilized across 4 architectural stages:
1. **Stage 1 (Database)**: Hardened Supabase Postgres with 160+ RLS policies.
2. **Stage 2 (Backend)**: FastAPI Core handling candidate state, jobs, analytics, and ARQ background processing.
3. **Stage 3 (AI/ML)**: High-speed WebSocket engine combined with a custom AI Gateway for scoring, fallback routing, and async claim-grounding.
4. **Stage 4 (UI)**: Cohesive dark-theme React frontend spanning Web and Desktop via robust Electron IPC bridges.

---

## 🚀 Getting Started: Complete Running Guide

Because of its strict decoupled architecture, running PRAXIS locally requires multiple services. **You will need 5 separate terminal windows.**

### Prerequisites
- Node.js (v20+) & `pnpm`
- Python (3.11+)
- Docker Desktop
- Supabase CLI (optional, but recommended for local DB pushes)

### Step 1: Environment Setup
Copy the example environment files and populate them with your API keys.
```bash
# In the root directory
cp .env.example .env

# REQUIRED in .env:
# GROQ_API_KEY=...
# OPENAI_API_KEY=... (or ANTHROPIC_API_KEY)
# NEXT_PUBLIC_SUPABASE_URL=...
# NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

### Step 2: Database & Infrastructure (Terminal 1)
Start the foundational infrastructure (Postgres, Redis for the ARQ workers, and Jaeger for tracing).
```bash
docker compose up -d
```
*(Migrations in `supabase/migrations` should apply automatically. If using local Supabase CLI, run `supabase start`)*

### Step 3: Frontend UIs (Terminal 2)
The UI components are managed via a `pnpm` monorepo workspace.
```bash
# Install all node dependencies across web, desktop, and packages
pnpm install

# Option A: Run the Next.js Web Dashboard (http://localhost:3000)
pnpm dev:web

# Option B: Run the Electron Desktop App (Practice Arena)
pnpm dev:desktop

# Option C: Run the shared UI Storybook
pnpm --filter @praxis/ui run storybook
```

### Step 4: Core Backend API (Terminal 3)
The core backend (`backend/app`) serves REST endpoints on port 8000.
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Start the REST API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: ARQ Background Workers (Terminal 4)
The backend uses `arq` and Redis to process slow tasks (like Resume Extraction) outside the HTTP cycle.
```bash
cd backend
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

arq worker_settings.WorkerSettings
```

### Step 6: Realtime Engine (Terminal 5)
The `realtime-agent` handles the live WebSocket interview stream, audio chunking, and VAD on port 8001.
```bash
cd realtime-agent
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# Install locally as an editable package (resolves ai-gateway dependency)
pip install -e .

# Start the WebSocket server
uvicorn realtime_agent.app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🧪 Testing Suites

Every layer of PRAXIS is heavily tested to ensure contracts remain strictly enforced.

**Frontend & Shared Packages (Node.js)**
```bash
# Run all tests (desktop, web, ui, packages)
pnpm test

# Typecheck everything
pnpm type-check
```

**Backend (Python / Pytest)**
```bash
cd backend
# activate venv
pytest tests/ -v
```

**Realtime Agent (Python / Pytest)**
```bash
cd realtime-agent
# activate venv
pytest tests/ -v
```

---

## 🧠 AI Providers & Cost Guardrails
PRAXIS implements a custom `packages/ai-gateway`. 
In the Dashboard Settings (`/settings/providers`), you can configure the Cost Mode:
- **FREE-FIRST**: Attempts to force local Ollama models.
- **BALANCED**: Prioritizes the free Groq tier (fastest inference for voice).
- **UNRESTRICTED**: Allows fallback to paid OpenAI/Anthropic APIs for deep reasoning or scoring tasks.

---

## 📚 Documentation
The codebase includes comprehensive Architectural Decision Records (ADRs) that explain *why* systems were built a specific way (e.g., why we avoided `react-router` in Electron, why scoring is asynchronous, etc.).
- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/STAGE_1_REPORT.md` (Database)
- `docs/STAGE_2_REPORT.md` (Backend API & Background Workers)
- `docs/STAGE_3_REPORT.md` (AI Gateway & Realtime Engine)
- `docs/STAGE_4_REPORT.md` (Frontend UI)