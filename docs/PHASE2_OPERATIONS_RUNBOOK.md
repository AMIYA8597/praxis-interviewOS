# PRAXIS InterviewOS — Phase 2 Operations Runbook

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Phase**: Phase 2 — AI/ML Intelligence Operations  
**Classification**: SRE / RUNBOOK SPECIFICATION  

---

## 1. Service Health & Readiness Verifications

### 1.1 Local Service Startup
```bash
# Terminal 1: Backend API
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Realtime WebSocket Agent
uvicorn realtime_agent.app.main:app --host 0.0.0.0 --port 8001

# Terminal 3: Background Worker
python -m arq backend.app.worker_tasks.WorkerSettings
```

### 1.2 Health Checks
- Core API: `GET http://localhost:8000/api/health`
- AI Providers Health: `GET http://localhost:8000/api/health/providers`
- Realtime Agent: `GET http://localhost:8001/health`

---

## 2. Audio & Speech-to-Text Troubleshooting

- **Symptom: High STT Latency (RTF > 0.8)**:
  - Check process CPU affinity. Verify `faster-whisper` has at least 2 dedicated CPU threads (`cpu_threads=2`).
  - Fall back to cloud STT by ensuring `GROQ_API_KEY` is provisioned.
- **Symptom: Audio WebSocket Drops**:
  - Check `WS_RECONNECT_GRACE_S` in `.env`. Ensure Redis is reachable so session state persists during reconnect.
- **Symptom: Barge-in not triggering**:
  - Check VAD threshold in `realtime_agent/app/audio/vad.py`. Default is 0.5 across 3 consecutive frames (96ms). In noisy environments, calibrate mic gain.
