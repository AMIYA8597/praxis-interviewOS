# PRAXIS InterviewOS — Performance, Load & Resilience Certification Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Benchmark Harness:** `scripts/benchmark_performance.py`  
**Execution Host:** Windows 11 AMD64 (8 GB RAM, 12 Cores)  

---

## 1. Measured Performance Baselines

| Component / Operation | Metric Measured | Tested Baseline | SLA Target | Status |
|---|---|:---:|:---:|:---:|
| **PostgreSQL Database Ping** | Round-trip latency (p50) | **0.50 ms** | < 5.0 ms | **PASS** |
| **PostgreSQL Database Ping** | Round-trip latency (p95) | **0.60 ms** | < 15.0 ms | **PASS** |
| **PostgreSQL Database Ping** | Round-trip latency (p99) | **60.21 ms** | < 100.0 ms | **PASS** |
| **Silero VAD (ONNX)** | Per-frame detection (p50) | **0.198 ms** | < 1.0 ms | **PASS** (160x faster than frame) |
| **Silero VAD (ONNX)** | Per-frame detection (p95) | **0.245 ms** | < 2.0 ms | **PASS** (130x faster than frame) |
| **Faster-Whisper STT (CPU int8)** | Realtime Factor (RTF) | **0.097** | < 0.30 | **PASS** (10.3x faster than real-time) |
| **Faster-Whisper STT (CPU int8)** | Transcription duration | **0.664 s** (for 6.88s audio) | < 2.0 s | **PASS** |
| **DSP Coaching Engine** | Cadence interval | **1.00 s strict** | 1.00 s | **PASS** (Independent of LLM delays) |
| **Synthetic E2E Journey** | Total full interview turn | **41.17 s** | < 60.0 s | **PASS** (All 10 relational entities) |
| **BGE Vector Embedding** | 384-dim batch latency | **14.2 ms / chunk** | < 50.0 ms | **PASS** |

---

## 2. Capacity Sizing Recommendations

Based on empirical performance measurements, the following Cloud Run and database capacities are certified:
- **`praxis-api`:** 1 vCPU, 1024 MiB RAM, concurrency 80, max 3 instances (staging), max 10 instances (prod).
- **`praxis-realtime`:** 1 vCPU, 2048 MiB RAM (int8 Whisper + Silero VAD footprint is ~850 MB), max 2 instances (staging), max 10 instances (prod).
- **`praxis-worker`:** 1 vCPU, 2048 MiB RAM, 1 instance (staging), max 5 instances (prod).
- **Database Pool:** 5 connections per API instance, 3 per realtime instance, 5 per worker instance.
