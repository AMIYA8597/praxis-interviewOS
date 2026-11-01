# PRAXIS InterviewOS — Realtime WebSocket & Audio Ingestion Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: REALTIME SECURITY AUDIT & SPECIFICATION  

---

## 1. Realtime Attack Surfaces & Architecture

The PRAXIS realtime speech agent listens on Port 8001 (`/ws/sessions/{session_id}`). It ingests high-frequency binary audio frames from candidates and orchestrates Faster-Whisper ASR, Silero VAD, and 1Hz coaching metrics.

```
[ Candidate Browser / Electron ]
       |
       | 1. WSS Handshake with JWT (?token=...)
       v
+=======================================================================+
| Handshake Security Gate                                               |
| - Validates RS256 JWT cryptographic signature against Supabase JWKS   |
| - Verifies candidate ownership of session_id in Redis session store   |
| - Rejects foreign or expired tokens immediately (Close 4001 / 4003)   |
+=======================================================================+
       |
       | 2. Binary Framing (>BBIdI 18-Byte Header + PCM16)
       v
+=======================================================================+
| Binary Frame Sanitization Gate                                        |
| - Minimum frame length check: len(frame) >= 18 bytes                  |
| - Protocol version check: proto_ver == 1                              |
| - Frame type validation: frame_type == 1 (AUDIO_FRAME)                |
| - Monotonic client_seq validation: drops duplicates & out-of-order    |
| - Payload length bounds check: payload_len <= 1048576 bytes           |
| - PCM16 alignment: payload_len % 2 == 0                               |
+=======================================================================+
       |
       | 3. Bounded Audio Ring Buffer
       v
[ Faster-Whisper ASR & Silero VAD Worker Pipeline ]
```

---

## 2. Invariants & Abuse Defenses

### 2.1 Monotonic Sequence Validation
To prevent replay attacks or corrupted speech reconstruction, the agent tracks `last_client_seq`. Any incoming frame with `client_seq <= last_client_seq` is rejected with `out_of_order_sequence` and dropped.

### 2.2 Bounded Memory & Audio Buffering
- **Maximum Frame Size**: Capped at 1MB per individual binary frame.
- **Turn Audio Quota**: Ingested PCM samples accumulate in a circular buffer capped at 30 seconds of active speech per turn (~960 KB). If a candidate exceeds turn limits, VAD triggers automatic turn finalization.
- **Connection Rate Limiting**: Per-user concurrent connection limit enforced via Redis. A candidate cannot open more than 2 concurrent WebSocket practice sessions simultaneously.

### 2.3 Degraded Fallback Mode Isolation
- If a candidate submits text answers via `candidate.text_answer` instead of audio frames, the text payload undergoes standard Pydantic validation (max 4,000 characters), preventing JSON buffer overflow.
