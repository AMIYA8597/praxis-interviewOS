# Realtime Protocol

WebSocket protocol specification for `praxis-realtime` (Cloud Run v2 service).

Service entry point: `realtime-agent/realtime_agent/app/main.py`
Endpoint: `wss://<host>/ws/{session_id}`

---

## Connection lifecycle

```
Client                         praxis-realtime
  │                                   │
  │──── WebSocket upgrade ───────────►│  Authorization: Bearer <JWT>
  │                                   │  (query param ?token=<JWT> fallback)
  │◄─── 101 Switching Protocols ──────│
  │                                   │  FSM state: CONNECTING → IDLE
  │──── {"type":"session.start", ────►│
  │      "session_id": "<uuid>"}       │  FSM: IDLE → ACTIVE
  │◄─── {"type":"session.started"} ───│
  │                                   │
  │──── audio frame (binary) ────────►│  VAD processes frame
  │     (16kHz PCM, 16-bit LE)        │  STT transcribes on speech end
  │◄─── {"type":"transcript", ────────│
  │      "text": "...",                │
  │      "final": true}                │
  │                                   │  LLM generates coaching response
  │◄─── {"type":"coaching", ──────────│
  │      "text": "..."}                │
  │◄─── audio frame (binary) ─────────│  TTS output (Piper)
  │                                   │
  │──── {"type":"session.end"} ───────►│  FSM: ACTIVE → CLOSING
  │◄─── {"type":"session.ended", ─────│
  │      "session_id": "<uuid>",       │
  │      "duration_s": 42}             │
  │                                   │  FSM: CLOSING → CLOSED
  │◄─── WebSocket close (1000) ───────│
```

---

## Session state machine (FSM)

States: `CONNECTING` → `IDLE` → `ACTIVE` → `CLOSING` → `CLOSED`

| State | Description | Valid transitions |
|-------|-------------|-------------------|
| `CONNECTING` | JWT verification in progress | → `IDLE` (success), → `CLOSED` (auth failure) |
| `IDLE` | Authenticated; waiting for `session.start` | → `ACTIVE`, → `CLOSED` |
| `ACTIVE` | Audio processing active | → `CLOSING`, → `CLOSED` (timeout) |
| `CLOSING` | Session end requested; flushing TTS | → `CLOSED` |
| `CLOSED` | Connection closed | — |

Idle timeout: 5 minutes (no audio frames received). Sends `{"type":"timeout"}` then closes with code 1001.
Max session duration: 90 minutes. Sends `{"type":"max_duration_reached"}` then closes.

---

## Message types

### Client → Server (JSON)

| Type | Fields | Description |
|------|--------|-------------|
| `session.start` | `session_id: uuid` | Begin a practice session |
| `session.end` | — | End the session cleanly |
| `ping` | — | Keep-alive |
| `hint.request` | `level: 1\|2\|3` | Request a hint at the specified level |
| `screenshot` | `data: base64` | Submit a screenshot for classification + coaching |

### Server → Client (JSON)

| Type | Fields | Description |
|------|--------|-------------|
| `session.started` | `session_id` | Session accepted and active |
| `session.ended` | `session_id`, `duration_s` | Session closed cleanly |
| `transcript` | `text`, `final: bool`, `confidence: float` | STT output |
| `coaching` | `text`, `source: "llm"\|"fallback"` | Coaching response |
| `hint` | `level: 1\|2\|3`, `text` | Hint response |
| `screenshot.result` | `classification`, `problem_statement` | Screenshot analysis |
| `error` | `code`, `message` | Protocol-level error |
| `timeout` | — | Idle timeout warning |
| `max_duration_reached` | — | Session duration limit hit |
| `pong` | — | Response to `ping` |

### Client → Server (binary)

Raw PCM audio frames: 16 kHz, 16-bit little-endian, mono.
Frame size: 20 ms (320 samples per frame).
Silero VAD processes each frame; STT is triggered on speech-end detection.

### Server → Client (binary)

Piper TTS audio: 22050 Hz, 16-bit PCM. Sent in 20 ms frames.

---

## Session recovery / reconnect

If the WebSocket connection drops mid-session:
1. Client may reconnect within 60 seconds with the same `session_id`.
2. `praxis-realtime` checks the `practice_sessions` table for an `active` session with that ID.
3. If found: resumes FSM from `ACTIVE`; does not re-send previous transcript.
4. If not found or `ended`/`abandoned`: returns `{"type":"error","code":"session_not_found"}`.

Cloud Run connection draining: 30-second drain on revision rollover. Clients with active
sessions during drain are closed with code 1001 (Going Away). Client must reconnect.

---

## Audio pipeline

```
PCM frames → Silero VAD → speech segments → faster-whisper STT → text
                                                                     │
                                              LLM coaching ◄─────────┤
                                                   │                 │
                                              Piper TTS              │
                                                   │                 │
                                              PCM frames             │
                                                   ▼                 ▼
                                           Client browser        transcript log
```

- **VAD:** Silero v4, 16 kHz, frame=20 ms, threshold=0.5
- **STT:** faster-whisper (base.en model), beam_size=5
- **TTS:** Piper (en_US-amy-medium voice)

All model files are baked into the Docker image at build time. No runtime downloads.

---

## Authentication

JWT is verified the same way as the REST API (RS256 JWKS). If verification fails,
the server immediately closes the WebSocket with code 4401 (application-level code).

Query-param fallback (`?token=<JWT>`) is supported for clients where `Authorization`
headers in WebSocket upgrades are not possible (e.g., browser `WebSocket` constructor).

---

## Known limitations

- Max concurrent WebSocket connections per Cloud Run instance: bounded by `WORKER_MAX_JOBS`
  setting (default 10). Scale `min_instance_count` and `max_instance_count` in Terraform to
  handle load.
- Cloud Run WebSocket timeout: 3600 s (1 hour). Long sessions approaching this limit receive
  `max_duration_reached` at 90 min by the application.
