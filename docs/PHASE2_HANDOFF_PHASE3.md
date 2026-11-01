# PRAXIS InterviewOS — Phase 3 Client Handoff Contract

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**From**: Phase 2 (AI/ML Intelligence Engine)  
**To**: Phase 3 (Web & Desktop UI Integration)  
**Classification**: API & REALTIME INTEGRATION CONTRACT (VERSION 1.0)  

---

## 1. Overview

This document specifies the authoritative, production-grade integration contract exposed by the PRAXIS AI/ML engine for `apps/web` (Next.js) and `apps/desktop` (Electron). Phase 3 UI engineers must adhere to these contracts. No business logic or scoring calculation should be implemented inside UI clients.

---

## 2. Realtime WebSocket Events & Lifecycle

**Endpoint**: `ws://<HOST>:8001/ws/sessions/{session_id}?token={JWT_ACCESS_TOKEN}`

### 2.1 Client-to-Server Events
1. **Audio Streaming (Binary Frames)**:
   - 18-byte big-endian header (`>BBIdI`): `proto_ver=1`, `frame_type=1`, `client_seq`, `capture_ts`, `payload_len`, followed by raw 16kHz mono 16-bit PCM samples (`int16`).
2. **Text Answer (Fallback/Degraded Mode)**:
   ```json
   {
     "type": "candidate.text_answer",
     "session_id": "uuid",
     "sequence": 12,
     "payload": {
       "text": "In microservices, we use distributed tracing..."
     }
   }
   ```
3. **Session Completion**:
   ```json
   {
     "type": "session.complete",
     "session_id": "uuid",
     "sequence": 13,
     "payload": {}
   }
   ```

### 2.2 Server-to-Client Events
1. **Audio Frame Acknowledgment**:
   ```json
   {
     "type": "audio.frame_ack",
     "session_id": "uuid",
     "sequence": 1,
     "payload": { "seq": 105, "received_ts": 1730467890.12 }
   }
   ```
2. **Streaming Transcripts**:
   - `transcript.partial`: Incremental, interim speech-to-text hypothesis for realtime caption rendering.
   - `transcript.final`: Finalized, punctuation-normalized turn segment.
3. **Realtime Coaching Metrics (Fast Path ~1Hz)**:
   ```json
   {
     "type": "coaching.metrics",
     "session_id": "uuid",
     "sequence": 4,
     "payload": {
       "wpm": 135.2,
       "filler_rate": 0.02,
       "duration_s": 42.5,
       "measurement_status": "MEASURED"
     }
   }
   ```
4. **Interviewer Question Spoken**:
   ```json
   {
     "type": "interviewer.text",
     "session_id": "uuid",
     "sequence": 5,
     "payload": {
       "text": "How did you manage database connection pooling under high load?",
       "repeat": false
     }
   }
   ```
5. **State Transitions**:
   ```json
   {
     "type": "state.transitioned",
     "session_id": "uuid",
     "sequence": 6,
     "payload": {
       "from": "AWAITING_ANSWER",
       "to": "CANDIDATE_TURN",
       "reason": "vad_speech_start"
     }
   }
   ```

---

## 3. Answer Evaluation & Measurement Status

All score objects returned by REST endpoints (`/api/sessions/{id}/debrief`) and WebSocket turn-end events conform to:

```json
{
  "rubric_version": "v1",
  "measurement_status": "MEASURED", 
  "relevance": 0.92,
  "correctness": 0.88,
  "structure": 0.85,
  "specificity": 0.90,
  "grounding": 1.00,
  "conciseness": 0.80,
  "overall": 0.89,
  "rationale": "Clear and detailed answer with accurate architectural justification.",
  "star_completeness": {
    "situation": true,
    "task": true,
    "action": true,
    "result": true
  }
}
```

### 3.1 Allowed `measurement_status` Values
- `MEASURED`: Full real evaluation succeeded.
- `ESTIMATED`: Evaluated with partial signals (e.g. text-only fallback).
- `DEGRADED`: One or more sub-services (like STT or audio metrics) degraded.
- `UNAVAILABLE`: Evaluation could not be performed (scores are `null`, never 0).

---

## 4. Evidence & Provenance Reference Format

When rendering candidate claims and debrief strengths/weaknesses in the UI:
```json
{
  "claim_text": "Reduced p95 API latency by 45% using Redis caching",
  "classification": "SUPPORTED",
  "supported": true,
  "confidence": 0.95,
  "source_chunk_id": "e4b2...-uuid",
  "source_project_id": "p81a...-uuid",
  "source_excerpt": "deployed a Redis cluster that reduced 95th percentile latency by 45%"
}
```

### 4.1 Claim Classification Values
- `SUPPORTED`: Proven fact backed by candidate documents. Render in Green.
- `PARTIALLY_SUPPORTED`: Overstated metrics or slight drift. Render in Yellow.
- `UNSUPPORTED`: Unverified by documents. Render in Neutral Gray with "Unverified" tag.
- `CONTRADICTED`: Conflicts with resume or earlier claims. Render in Red with warning badge.
- `UNCERTAIN`: Ambiguous context. Render in Light Gray with "Needs Clarification".

---

## 5. PRAXIS Readiness Estimate

Endpoint: `GET /api/readiness/candidates/{candidate_id}`
- Response includes explicit disclaimer: "PRAXIS Readiness Estimate is a calibrated preparatory indicator, not an employment guarantee."
- If `session_count < 1`: Returns `null` readiness with status `"INSUFFICIENT_EVIDENCE"`. UI must prompt the candidate to complete their first mock practice session.
