# PRAXIS Local Development Guide

## 1. Prerequisites

- **Python**: 3.11.x (Repository strictly runs Python 3.11).
- **Package Managers**: `uv` (recommended) or `pip`.
- **Node.js**: v20+ and `pnpm` (for frontend / web workspaces).
- **PostgreSQL**: PostgreSQL 17 with `pgvector` extension installed.
- **Redis**: Redis 7+ server.
- **Docker**: Docker Desktop (optional, for local container validation).

---

## 2. Environment Setup

### 2.1 Clone Repository & Initialize Python Virtual Environment
```powershell
# Create Python 3.11 virtual environment
uv venv .venv --python 3.11

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

### 2.2 Install Dependencies
```powershell
# Install core backend requirements and testing tools
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio respx ruff fakeredis pip-audit

# Install editable repository packages
pip install -e packages/config
pip install -e packages/ai-gateway
pip install -e backend
pip install -e realtime-agent
```

### 2.3 Configure Environment Variables
Copy `.env.example` to `.env` and configure your local connection strings:
```ini
APP_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/praxis
REDIS_URL=redis://localhost:6379/0
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./storage
```

---

## 3. Database Migrations

Apply the 31 Supabase SQL migrations to your database:
```powershell
python scripts/migrate.py
```
To verify idempotency, run a second time (must apply 0 migrations):
```powershell
python scripts/migrate.py
```

---

## 4. Starting Backend Services Locally

Open separate terminal windows for each independent service:

### 4.1 Core REST API
```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health probe: `http://localhost:8000/health/live`
- Migration status: `http://localhost:8000/health/startup`

### 4.2 Realtime WebSocket Agent
```powershell
uvicorn realtime_agent.app.main:app --host 0.0.0.0 --port 8080 --reload
```
- Realtime WebSocket: `ws://localhost:8080/ws/sessions/{session_id}`

### 4.3 Background ARQ Worker
```powershell
python -m arq backend.worker_settings.WorkerSettings
```

---

## 5. Running Quality & Verification Gates

### 5.1 Code Formatting & Linting
```powershell
ruff check .
ruff format --check .
```

### 5.2 Architectural Boundary Verification
```powershell
python scripts/check_no_fake_data.py
python scripts/check_gateway_boundary.py
python scripts/check_prompt_construction_boundary.py
python scripts/check_backend_completeness.py
```

### 5.3 Automated Test Suites
```powershell
# Run backend test suite
pytest backend/tests/ -q -rs -m "not live_provider"

# Run security & hardening suite
pytest backend/tests/security/ backend/tests/hardening/ -v

# Run AI gateway & realtime agent suite
pytest packages/ai-gateway/tests/ realtime-agent/tests/ -q -rs -m "not live_provider"

# Run contract verification
pytest backend/tests/api/test_openapi_contract.py
```
