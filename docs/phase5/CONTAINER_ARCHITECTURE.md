# PRAXIS InterviewOS — Container Architecture & Hardening

**Document ID**: PROD-CONT-001  
**Milestone**: Phase 5 — Production Engineering  
**Base Image**: `python:3.11.11-slim` (Debian Bookworm)  
**Security Standard**: Non-Root UID 10001, Hash-Verified Lockfiles, Multi-Stage Builds  
**Date**: 2026-11-01  
**Status**: Authoritative Container Specification  

---

## 1. Container Build Design & Multi-Stage Architecture

All PRAXIS microservices utilize Docker BuildKit syntax (`# syntax=docker/dockerfile:1.7`) and follow a strict 3-stage pattern to ensure minimal, reproducible, and vulnerability-free runtime artifacts:

```mermaid
flowchart TD
    subgraph Stage 1: Build Dependencies
        Deps[python:3.11.11-slim\nInstall build-essential, libpq-dev\nCreate venv /venv\npip install --require-hashes]
    end

    subgraph Stage 2: Source Packaging
        Source[deps base\nCopy packages/, backend/, realtime/\npip install --no-deps (non-editable)\nBake ML models if realtime]
    end

    subgraph Stage 3: Production Runtime
        Prod[python:3.11.11-slim minimal\nInstall runtime libpq5, libsndfile1\nCreate user praxis UID 10001\nCopy /venv and /app from source\nEXPOSE port & HEALTHCHECK]
    end

    Deps --> Source --> Prod
```

### Key Guarantees
1. **Zero Compiler Artifacts in Production**: Build tools (`gcc`, `g++`, `make`, `python3-dev`) are isolated in `deps` and discarded.
2. **Deterministic Hashes**: Dependencies are installed using `--require-hashes` matching `requirements-lock.txt` to eliminate supply chain tampering.
3. **Non-Editable Package Installation**: Python packages are installed without `-e` to avoid fragile symlinks and ensure complete standalone directory encapsulation inside `/app`.
4. **Least-Privilege Non-Root Execution**: Every container defines `groupadd -g 10001 praxis && useradd -u 10001 -r -g praxis -d /app praxis` and runs with `USER praxis`.

---

## 2. Microservice Container Breakdown

### 2.1 API Service Container (`docker/Dockerfile.api`)
- **Base Image**: `python:3.11.11-slim`
- **Exposed Port**: `8000`
- **System Dependencies**: `libpq5`, `tesseract-ocr`, `curl`
- **Healthcheck**: `curl -fsS http://localhost:8000/health || exit 1` (interval: 30s, timeout: 10s, start-period: 60s)
- **Startup Entrypoint**:
  ```bash
  uvicorn backend.app.main:app \
      --host 0.0.0.0 \
      --port ${PORT} \
      --workers 1 \
      --timeout-graceful-shutdown 30 \
      --log-config /dev/null \
      --no-access-log
  ```
- **Estimated Image Size**: $\approx 220\text{ MB}$ uncompressed.

### 2.2 Realtime Audio Service Container (`docker/Dockerfile.realtime`)
- **Base Image**: `python:3.11.11-slim`
- **Exposed Port**: `8080`
- **System Dependencies**: `libsndfile1`, `ffmpeg`, `libgomp1`, `curl`
- **Pre-Baked ML Models**:
  - `faster_whisper` (`small`, `cpu`, `compute_type='int8'`)
  - `silero_vad` (ONNX model)
  - Pre-downloaded at image build time into `/app/.cache` with `chown -R praxis:praxis /app/.cache`.
- **Offline Environment Flags**:
  ```env
  HF_HOME=/app/.cache/huggingface
  HF_HUB_OFFLINE=1
  XDG_CACHE_HOME=/app/.cache
  ```
- **Healthcheck**: `curl -fsS http://localhost:8080/health || exit 1` (interval: 30s, timeout: 10s, start-period: 90s)
- **Startup Entrypoint**:
  ```bash
  uvicorn realtime_agent.app.main:app \
      --host 0.0.0.0 \
      --port ${PORT} \
      --workers 1 \
      --timeout-graceful-shutdown 30 \
      --log-config /dev/null \
      --no-access-log
  ```
- **Estimated Image Size**: $\approx 850\text{ MB}$ (including PyTorch CPU, torchaudio, and quantized Whisper weights).

### 2.3 Background Worker Container (`docker/Dockerfile.worker`)
- **Base Image**: `python:3.11.11-slim`
- **Exposed Port**: `8080` (Internal HTTP health probe)
- **System Dependencies**: `libpq5`, `tesseract-ocr`, `libsndfile1`, `curl`
- **Startup Entrypoint**:
  ```bash
  python -m arq backend.worker_settings.WorkerSettings
  ```
- **Healthcheck**: `curl -fsS http://localhost:8080/health || exit 1` (interval: 30s, timeout: 10s, start-period: 30s)
- **Estimated Image Size**: $\approx 240\text{ MB}$.

### 2.4 Code Execution Sandbox (`docker/Dockerfile.sandbox`)
- **Base Image**: Minimal, hardened scratch/alpine execution runner
- **Security**: Zero network egress, read-only root filesystem, dropped capabilities, memory bounded to 256 MiB, CPU timeout capped at 5 seconds.

---

## 3. Container Security Verification Matrix

| Security Control | Implementation | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Non-Root Execution** | UID 10001 (`praxis`) | `id` inspection inside container | **ENFORCED** |
| **No Embedded Secrets** | Build arguments & `.dockerignore` | Secret leakage scanner gate | **VERIFIED** |
| **Deterministic Dependencies** | Pip `--require-hashes` | BuildKit hash check against lockfiles | **ENFORCED** |
| **Offline Model Loading** | `HF_HUB_OFFLINE=1` | Air-gapped startup test | **VERIFIED** |
| **Graceful Shutdown** | 30s SIGTERM handling in Uvicorn | Container stop probe | **ENFORCED** |
