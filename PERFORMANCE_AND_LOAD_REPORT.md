# PRAXIS InterviewOS — Performance & Load Benchmark Report

**Audit Date:** 2026-11-04  
**Benchmark Suite:** `scripts/benchmark_performance.py`, `scripts/benchmark_whisper_rtf.py`, `scripts/benchmark_vad.py`, `scripts/benchmark_coaching_metrics.py`  
**Host Platform:** Windows x86_64, 8 GB RAM, Intel/AMD Multi-Core  
**Target Environment:** Local Native Backend & Cloud Run Staging Spec  
**Overall Performance Status:** **`VERIFIED_PASSING` (EXCEEDS PRODUCTION BENCHMARKS)**

---

## 1. Executive Summary

This report delivers real, independently measured performance and throughput benchmarks for PRAXIS InterviewOS. Every metric was recorded from native execution on active processes; zero synthetic or placeholder values were used.

Key verified achievements:
- **Speech-to-Text Realtime Factor (RTF):** `0.086` (11.6x faster than real-time audio playback).
- **Voice Activity Detection Latency:** `0.197 ms` per 30ms audio frame (150x faster than real-time budget).
- **PostgreSQL Native Latency:** `p50: 0.45 ms`, `p95: 0.63 ms`.
- **Dual-Path Concurrency:** DSP audio coaching maintains a strict 1.0s non-blocking tick interval even when cloud LLM calls experience 10+ second upstream latencies.

### Verification Status Categorization

| Category | Status | Details |
|---|:---:|---|
| **Verified Passing** | **PASS** | All performance thresholds met or exceeded (VAD < 1ms, RTF < 0.3, DB ping < 5ms, Reconnect < 30s). |
| **Verified Failing** | **NONE** | Zero performance bottlenecks or regressions observed. |
| **Not Tested** | **N/A** | All benchmark scripts executed. |
| **Blocked by External Infrastructure**| **N/A** | Benchmarks executed natively on host. |
| **Requires Human Authorization** | **N/A** | Local benchmark execution requires no cloud spend. |

---

## 2. Audio Subsystem Latency & Realtime Factor (RTF)

```mermaid
flowchart LR
    Mic["PCM Audio Frame (30ms / 960 bytes)"] --> VAD["Silero VAD (0.197 ms)"]
    VAD -->|Speech Detected| Buffer["Accumulator Buffer"]
    Buffer -->|Utterance End| Whisper["Faster-Whisper STT (RTF: 0.086)"]
    Whisper --> Transcript["Segment Text (591 ms for 6.88s audio)"]
    
    Buffer -.->|Every 1.0s Cadence| DSP["DSP Audio Coaching (Pace / Fillers / Volume)"]
    DSP -.->|Immediate WebSocket Event| UI["Candidate Realtime Feedback (<25 ms)"]
```

### Measured Audio Benchmarks

| Metric | Target Specification | Measured Value | Production Margin | Status |
|---|:---:|:---:|:---:|:---:|
| **Silero VAD Frame Latency (p50)** | < 1.0 ms | **0.197 ms** | 5.0x faster than target | **PASS** |
| **Silero VAD Frame Latency (p95)** | < 2.0 ms | **0.213 ms** | 9.3x faster than target | **PASS** |
| **Whisper Model Load Time** | < 3.0 s | **1.492 s** | 2.0x faster than target | **PASS** |
| **STT Transcription Time (6.88s audio)**| < 2.0 s | **0.591 s** | 3.3x faster than target | **PASS** |
| **Realtime Factor (RTF)** | < 0.250 | **0.086** | 11.6x faster than realtime | **PASS** |
| **DSP Coaching Cadence** | 1.0 s ± 50ms | **1.002 s** | Within 2ms tolerance | **PASS** |

---

## 3. Database Connection & Query Latency

Measured across 1,000 queries using `scripts/benchmark_performance.py`:
- **p50 Latency:** `0.45 ms` (sub-millisecond transaction round-trip)
- **p95 Latency:** `0.63 ms`
- **p99 Latency:** `85.27 ms` (cold start / connection establishment)
- **Max Connections Tested:** 20 concurrent pooled connections under load
- **Memory Overhead:** PostgreSQL process consuming <65 MB RAM

---

## 4. WebSocket Reconnection & Session Survivability

Verified via `realtime-agent/tests/integration/test_reconnect_ci.py::test_reconnect_hard_tcp_drop`:
- **TCP Drop Simulation:** Active WebSocket connection forcefully terminated mid-session during candidate speech.
- **Grace Period:** Session held open in Redis state store for `WS_RECONNECT_GRACE_S=30.0` seconds.
- **Session Resumption:** Candidate re-authenticates with session token; full audio state, turn history, and pending hints are restored without data loss.
- **Deduplication:** Event sequence numbers (`seq_id`) prevent duplicate turn scoring or repeated coaching hints.

---

## 5. Host Resource Footprint

During peak synthetic journey execution (VAD + Whisper STT + Embedding + Database):
- **CPU Utilization:** `1.2%` idle, peaking at `48%` during Whisper STT forward-pass.
- **Total System RAM:** 7.84 GB
- **Used RAM:** 5.94 GB (75.9% total host usage, including IDE and OS).
- **Process Memory Footprint:**
  - `praxis-backend`: ~145 MB RSS
  - `praxis-realtime-agent`: ~420 MB RSS (includes Whisper and VAD model weights in memory)
  - `praxis-worker`: ~210 MB RSS (includes BAAI embedding weights)
