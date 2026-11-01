# PRAXIS InterviewOS — Phase 3 Realtime Client Protocol & State Machine

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: REALTIME NETWORKING SPECIFICATION  

---

## 1. Client State Machine

The client WebSocket connection progresses through a deterministic finite state machine:

```
[ DISCONNECTED ]
       | (connect())
       v
[ CONNECTING ]
       | (token acquired & socket opened)
       v
[ AUTHENTICATING ]
       | (auth accepted & session bound)
       v
[ READY ] <------------------------+
       | (mic active / turns flowing)|
       v                             |
[ CANDIDATE_TURN ]                   | (turn complete)
       | (interviewer speaking)      |
       v                             |
[ INTERVIEWER_TURN ] ----------------+
       |
       | (on error / drop)
       v
[ RECONNECTING ] (Exponential Backoff with Jitter)
       | (max retries exceeded)
       v
[ FAILED ]
```

---

## 2. Event Catalog

### 2.1 Client to Server
1. **Binary Audio Frame**: 18-byte big-endian header + PCM16 samples.
2. **Text Answer Fallback**:
   ```json
   {
     "type": "candidate.text_answer",
     "session_id": "uuid",
     "sequence": 4,
     "payload": { "text": "In distributed systems, eventual consistency..." }
   }
   ```
3. **Session Completion**:
   ```json
   {
     "type": "session.complete",
     "session_id": "uuid",
     "sequence": 5,
     "payload": {}
   }
   ```

### 2.2 Server to Client
1. `audio.frame_ack`: Client sequence number and server arrival timestamp.
2. `transcript.partial`: Streaming hypothesis for live speech captions.
3. `transcript.final`: Punctuation-normalized committed turn.
4. `coaching.metrics`: Realtime ~1Hz speech metrics (WPM, filler rate, duration).
5. `interviewer.text`: Synthesized question spoken by the interviewer.
6. `state.transitioned`: Session turn updates.

---

## 3. Resilience & Sequence Reconciliation
- **Exponential Backoff with Jitter**: Reconnection delays follow `min(base * 2^attempt, max_delay) * (0.5 + 0.5 * rand())`.
- **Sequence Reconciliation**: Incoming events track `seq` numbers; any duplicate event received during reconnect is dropped without duplicate UI rendering.
- **Heartbeat Detection**: Periodic `ping/pong` every 20 seconds ensures dropped connections are detected and recovered within 5 seconds.
