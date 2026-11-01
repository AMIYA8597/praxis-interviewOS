# PRAXIS InterviewOS — WebSocket Abuse & Resilience Test Matrix

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: REALTIME ADVERSARIAL TEST REPORT  

---

## 1. Adversarial Test Catalog

| Test ID | Attack Scenario | Injected Payload | Expected Defense Behavior | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| `WS-01` | Missing JWT token parameter | `ws://host:8001/ws/sessions/{id}` | Connection rejected (HTTP 401 / Close 4001) | **PASS** |
| `WS-02` | Expired JWT token | `ws://host:8001/ws/sessions/{id}?token={expired}` | Connection rejected (Close 4001) | **PASS** |
| `WS-03` | Candidate B connecting to Alice's session | `ws://host:8001/ws/sessions/{alice_id}?token={bob}` | Connection rejected (Close 4003 Forbidden) | **PASS** |
| `WS-04` | Truncated binary frame (<18 bytes) | 12 bytes of random binary data | Server sends `malformed_audio_frame`, connection preserved | **PASS** |
| `WS-05` | Invalid protocol version (`proto_ver=99`) | 18-byte header with byte 0 = `99` | Server sends `unsupported_protocol` error | **PASS** |
| `WS-06` | Invalid frame type (`frame_type=255`) | 18-byte header with byte 1 = `255` | Server sends `invalid_frame_type` error | **PASS** |
| `WS-07` | Replay / duplicate sequence number | Frame with `seq=10` sent twice | Duplicate frame dropped with `out_of_order_sequence` | **PASS** |
| `WS-08` | Decreasing sequence number | Frame with `seq=5` after `seq=10` | Frame dropped with `out_of_order_sequence` | **PASS** |
| `WS-09` | Oversized payload claim (`payload_len=50MB`) | 18-byte header claiming 50MB payload | Server sends `oversized_frame` error | **PASS** |
| `WS-10` | Payload length mismatch | Header claims 1000 bytes, sends 100 bytes | Server sends `malformed_audio_frame` error | **PASS** |
| `WS-11` | Odd PCM byte count | 18-byte header followed by 501 bytes | Server sends `malformed_audio_frame` (must be even for int16) | **PASS** |
| `WS-12` | Malformed JSON in text message | Invalid JSON string `"{bad"` | Caught safely in try/except; worker does not crash | **PASS** |

---

## 2. Automated Test Execution
- Protocol unit tests: `realtime-agent/tests/test_audio_protocol.py` (35 tests passing).
- Realtime integration tests: `realtime-agent/tests/integration/test_e2e_acceptance.py`.
