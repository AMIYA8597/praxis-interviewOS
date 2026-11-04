# PRAXIS InterviewOS — Resource Sizing & Capacity Recommendations

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Service Resource Sizing Matrix

| Component | Target vCPU | Target RAM | Container Concurrency | Scaling Bounds (Staging) | Scaling Bounds (Production) |
|---|---|---|---|---|---|
| **`praxis-api`** | 1.0 vCPU | 1024 MiB | 80 requests | Min: 0, Max: 3 | Min: 1, Max: 10 |
| **`praxis-realtime`** | 1.0 vCPU | 2048 MiB | 10 connections | Min: 1, Max: 2 | Min: 2, Max: 10 |
| **`praxis-worker`** | 1.0 vCPU | 2048 MiB | 5 concurrent jobs | Fixed: 1 instance | Min: 1, Max: 5 |
| **`praxis-sandbox`** | 0.5 vCPU | 512 MiB | 1 execution | Min: 0, Max: 2 | Min: 1, Max: 5 |

---

## 2. Memory Footprint Breakdown

- **Realtime Image Memory:**
  - Base OS & Python runtime: ~120 MiB
  - Faster-Whisper `small` int8 model in RAM: ~480 MiB
  - Silero VAD ONNX model: ~35 MiB
  - Operational buffer headroom: ~400 MiB
  - Total allocation of 2048 MiB provides over 2x safety margin against OOM kills.
- **Worker Image Memory:**
  - ARQ task queue worker: ~150 MiB
  - BGE embedding model: ~130 MiB
  - PDF/DOCX parsing & OCR buffers: ~350 MiB
  - Total allocation of 2048 MiB handles concurrent multi-page resume extraction smoothly.
