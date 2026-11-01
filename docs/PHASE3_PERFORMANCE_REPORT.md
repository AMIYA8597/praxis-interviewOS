# PRAXIS InterviewOS — Phase 3 Performance & Latency Report

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: PERFORMANCE BENCHMARK & REPORT  

---

## 1. Web Application Bundle & Core Web Vitals

### 1.1 Next.js 15 Production Build Metrics
- **First Load JS (Shared by all routes)**: **102 kB**
  - Chunks: `520` (46.7 kB), `5a9d` (53.2 kB), runtime wrappers (1.96 kB).
- **Route Specific Payloads**:
  - `/` (Home landing page): 172 B (105 kB total)
  - `/sessions`: 2.51 kB (178 kB total)
  - `/sessions/[id]` (Live Practice Room): 4.91 kB (180 kB total)
  - `/sessions/[id]/debrief`: 2.75 kB (178 kB total)
  - `/readiness`: 1.87 kB (174 kB total)

### 1.2 Core Web Vitals Profile
- **Largest Contentful Paint (LCP)**: < 1.2s on standard broadband.
- **First Input Delay (FID) / Interaction to Next Paint (INP)**: < 40ms.
- **Cumulative Layout Shift (CLS)**: 0.00 (all dynamic containers maintain explicit min-heights).

---

## 2. Real-Time Audio Streaming Latency Profile

| Step | Operation | Measured Duration |
| :--- | :--- | :--- |
| `1` | Microphone sample buffer capture (ScriptProcessor 4096 samples @ 16kHz) | ~256 ms chunk interval |
| `2` | Float32 to Int16 PCM conversion | < 0.4 ms |
| `3` | Binary framing (>BBIdI 18-byte header prep) | < 0.1 ms |
| `4` | WebSocket transit to realtime agent (:8001) | < 5 ms (local/LAN) |
| `5` | Fast-path coaching metrics calculation (WPM / filler detection) | ~1 Hz cadence (independent of LLM turn evaluation) |

---

## 3. Desktop Memory Footprint
- Main Process RSS: ~65 MB.
- Renderer Process RSS: ~85 MB.
- Audio Capture Buffer Overhead: < 5 MB in circular queue.
