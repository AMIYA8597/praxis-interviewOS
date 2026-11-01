# PRAXIS InterviewOS — Phase 3 Operations & Client Runbook

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: RUNBOOK & DEPLOYMENT GUIDE  

---

## 1. Environment Configurations

### 1.1 Web Application (`apps/web/.env.local`)
```ini
NEXT_PUBLIC_SUPABASE_URL=https://<YOUR_PROJECT>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<ANON_KEY>
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_REALTIME_URL=ws://localhost:8001
```

### 1.2 Desktop Application
```ini
VITE_SUPABASE_URL=https://<YOUR_PROJECT>.supabase.co
VITE_SUPABASE_ANON_KEY=<ANON_KEY>
VITE_API_BASE_URL=http://localhost:8000
VITE_REALTIME_URL=ws://localhost:8001
```

---

## 2. Client Startup & Local Development

### Starting the Web Client:
```bash
pnpm --filter web dev
# Listens on http://localhost:3000
```

### Starting the Desktop Client:
```bash
pnpm --filter desktop dev
# Launches Electron development window with hot reload
```

### Monorepo Build:
```bash
pnpm build:desktop
pnpm build:web
```

---

## 3. Operational Troubleshooting

| Symptom | Diagnostic Step | Mitigation |
| :--- | :--- | :--- |
| Microphone permission denied | Inspect browser URL lock icon or system privacy settings | Click "Grant Microphone Permission" in `AudioControl` |
| WebSocket connection failed | Check if `realtime-agent` is running on port 8001 | Verify JWT token validity; ensure backend worker processes are healthy |
| Debrief status stuck on "pending" | Verify Redis queue worker status | Check `celery/worker` logs for debrief generation completion |
| No readiness score displayed | Inspect candidate session count | Ensure candidate has finished at least 1 practice session |
