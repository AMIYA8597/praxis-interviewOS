# PRAXIS InterviewOS — Authoritative Build Boundary & Backend Packaging

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Implementation Standard:** Option B (Monorepo Build Context with Strict Service Boundaries)  

---

## 1. Authoritative Deployment Boundary Decision

To ensure deterministic, reproducible builds without duplicating business logic, PRAXIS adopts **Option B**:
- The Docker build context is the repository root (`.`), allowing backend containers to package internal shared libraries (`packages/config`, `packages/ai-gateway`).
- Each service's Dockerfile explicitly copies **only** its strictly required runtime dependencies and completely excludes frontend applications (`apps/web`, `apps/desktop`, `packages/ui`).
- No build step requires Node.js, Next.js, Electron, or Webpack in any backend container.
- All dependencies are pinned with full SHA-256 cryptographic hashes in `docker/requirements/*.lock`.

```
Repository Root (Build Context)
├── backend/                  ---> Included in praxis-api, praxis-worker, praxis-realtime
├── packages/
│   ├── config/              ---> Included in all backend services
│   ├── ai-gateway/          ---> Included in all backend services
│   ├── ui/                  ---> EXCLUDED from all backend containers
├── realtime-agent/           ---> Included in praxis-realtime only
├── prompts/                  ---> Included in all backend services
├── docker/
│   ├── Dockerfile.api       ---> Builds praxis-api
│   ├── Dockerfile.realtime  ---> Builds praxis-realtime
│   ├── Dockerfile.worker    ---> Builds praxis-worker
│   ├── Dockerfile.sandbox   ---> Builds praxis-sandbox
│   └── requirements/*.lock  ---> Hash-pinned lockfiles
├── apps/
│   ├── web/                 ---> STRICTLY EXCLUDED
│   └── desktop/             ---> STRICTLY EXCLUDED
```

---

## 2. Service Boundary Audit

### 2.1 `praxis-api`
- **Source Paths:** `backend/`, `packages/config/`, `packages/ai-gateway/`, `prompts/`.
- **Excluded Paths:** `apps/**`, `packages/ui/**`, `realtime-agent/**`, `tests/**`.
- **System Dependencies:** `python:3.11.11-slim`, `libpq5`, `tesseract-ocr`, `curl`.
- **Lockfile:** `docker/requirements/api.lock` (hash-verified).
- **Execution User:** `praxis` (UID 10001, non-root).
- **Runtime Port:** `8000` (`HEALTHCHECK` on `/health`).

### 2.2 `praxis-realtime`
- **Source Paths:** `realtime-agent/`, `backend/`, `packages/config/`, `packages/ai-gateway/`, `prompts/`.
- **Excluded Paths:** `apps/**`, `packages/ui/**`, `tests/**`.
- **Excluded Libraries:** Desktop-only audio capture libraries (`sounddevice`, `pyaudio`, `portaudio`).
- **System Dependencies:** `python:3.11.11-slim`, `libsndfile1`, `ffmpeg`, `libgomp1`, `curl`.
- **Baked Model Assets:** `faster-whisper` (`small` int8 model) and `silero-vad` (ONNX) baked into `/app/.cache` at build time.
- **Offline Guard:** `HF_HUB_OFFLINE=1` prevents runtime network egress during cold starts.
- **Execution User:** `praxis` (UID 10001, non-root).
- **Runtime Port:** `8080` (`HEALTHCHECK` on `/health`).

### 2.3 `praxis-worker`
- **Source Paths:** `backend/`, `packages/config/`, `packages/ai-gateway/`, `prompts/`.
- **Excluded Paths:** `apps/**`, `packages/ui/**`, `realtime-agent/**`, `tests/**`.
- **System Dependencies:** `python:3.11.11-slim`, `libpq5`, `tesseract-ocr`, `libsndfile1`, `curl`.
- **Lockfile:** `docker/requirements/worker.lock` (hash-verified).
- **Execution User:** `praxis` (UID 10001, non-root).
- **Runtime Port:** `8080` (HTTP health listener on `/health`).
- **Entrypoint:** `python -m arq backend.worker_settings.WorkerSettings`.

### 2.4 `praxis-sandbox`
- **Source Paths:** `backend/app/sandbox_service.py`.
- **Excluded Paths:** All application secrets, database connections, Redis pools, and other backend code.
- **Security Posture:** Dedicated `sandbox` user (UID 10001), no network egress, hard resource caps (CPU, memory, file descriptors).
- **Runtime Port:** `8001` (`HEALTHCHECK` on `/health/live`).

---

## 3. Monorepo Isolation & Boundary Verification

1. **Foreign Imports Audit:** Confirmed **0 imports** from `apps/`, `web/`, or `desktop/` across `backend`, `packages/ai-gateway`, and `realtime-agent`.
2. **Absolute Path Audit:** Confirmed **0 developer-machine absolute paths** in production code.
3. **No Dev Dependencies in Images:** Images use multi-stage builds (`deps` -> `source` -> `production`) discarding compiler tools (`build-essential`, `libpq-dev`) in the final layer.
4. **No Git, Secrets, or Env Files:** Docker context excludes `.git`, `.env*`, and local databases via `.dockerignore`.
