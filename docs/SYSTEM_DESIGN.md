PART 2 — SYSTEM DESIGN
2.1 Top-level architecture
┌──────────────────────────────────────────────────────────────────────┐
│                   ELECTRON DESKTOP CLIENT (Windows 11)               │
│                                                                      │
│  main/          preload/        renderer/ (React, shared UI pkg)     │
│  ├ audio/       ├ typed IPC     ├ Practice Arena (live)              │
│  │  ├ mic         allowlist     ├ Coaching HUD                       │
│  │  ├ loopback                  ├ Transcript pane                    │
│  │  └ VAD (local)               ├ Study Workbench                    │
│  ├ capture/screenshot           └ Diagnostics                        │
│  ├ shortcuts/ (global)                                               │
│  ├ secureStore/ (OS credential vault — safeStorage / DPAPI)          │
│  └ updater/                                                          │
└───────────────┬──────────────────────────────────┬───────────────────┘
                │ WebSocket (audio frames + events)│ HTTPS (REST)
                ▼                                  ▼
┌───────────────────────────────┐   ┌──────────────────────────────────┐
│   REALTIME AGENT (Python)     │   │   FASTAPI CORE API (Python)      │
│                               │   │                                  │
│  session state machine        │   │  auth • candidates • resumes     │
│  frame ingest + reorder       │   │  projects • jobs • sessions      │
│  turn detector                │◀─▶│  study • outreach • analytics    │
│  barge-in controller          │   │  admin • health • billing-stub   │
│  STT orchestrator             │   └────────┬─────────────────────────┘
│  interviewer policy engine    │            │
│  coaching feature extractor   │            ▼
│  answer scorer                │   ┌──────────────────────────────────┐
│  TTS orchestrator             │   │  WORKERS (arq / Redis queue)     │
└───────────────┬───────────────┘   │  doc parse • embed • analytics   │
                │                   │  research • cleanup • exports    │
                ▼                   └────────┬─────────────────────────┘
     ┌──────────────────────┐                │
     │    AI GATEWAY        │◀───────────────┘
     │  capability registry │
     │  router + policies   │
     │  circuit breakers    │
     │  budget guard        │
     │  telemetry           │
     └──────────┬───────────┘
                │
   ┌────────┬───┴────┬─────────┬─────────┬──────────┐
   ▼        ▼        ▼         ▼         ▼          ▼
 Ollama   Groq    Gemini   OpenAI   Anthropic   DeepSeek/xAI
 (local)  (free)  (free)   (BYO)    (BYO)       (BYO)
   │
   └── local: faster-whisper · bge-small · PaddleOCR · Piper TTS

                ┌──────────────────────────────────────┐
                │  SUPABASE FREE TIER                  │
                │  Postgres · pgvector · Auth ·        │
                │  Storage · RLS · Realtime            │
                └──────────────────────────────────────┘
                ┌──────────────────────────────────────┐
                │  REDIS (local Docker / Upstash free) │
                │  queue · cache · session state · rl  │
                └──────────────────────────────────────┘
Why this shape
The Realtime Agent is a separate process from the Core API. A slow analytics query must never add jitter to an audio frame path. They share the database and the AI Gateway, nothing else. This also lets you scale them independently later without a rewrite.
The AI Gateway is the only place a provider SDK is imported. Grep the repo: import openai should appear in exactly one file. This is what makes the failover demo possible and what makes "we are not vendor-locked" a true statement instead of a slide.
Electron owns media, and nothing else. No AI orchestration in the main process, no database access from the renderer. The main process is a privileged media and OS-integration shim with a typed IPC allowlist.
Local models are the default path, not the fallback. In LOCAL_ONLY mode the app is fully functional on a laptop with no API keys. Cloud providers are an upgrade, which is the opposite of how most projects are built and is a genuinely defensible free-first architecture.
2.2 The realtime loop (the core, in detail)
                        ┌───────────────────────────┐
                        │  AI INTERVIEWER TURN      │
                        │  policy → question text   │
                        │  → TTS → playback         │
                        └────────────┬──────────────┘
                                     │
                    ┌────────────────┴─────────────────┐
                    │  BARGE-IN WATCH (always armed)   │
                    │  if candidate VAD fires during   │
                    │  playback → duck, stop TTS,      │
                    │  cancel generation, yield turn   │
                    └────────────────┬─────────────────┘
                                     ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  CANDIDATE TURN                                              │
    │                                                              │
    │  mic 16 kHz mono ─▶ resample ─▶ RNNoise/WebRTC NS ─▶ AGC     │
    │        │                                                     │
    │        ├─▶ Silero VAD (ONNX, local, ~1 ms/frame)             │
    │        │      └─▶ speech_start / speech_end / energy         │
    │        │                                                     │
    │        ├─▶ 320 ms chunks ─▶ STT stream ─▶ partial/final      │
    │        │                                                     │
    │        └─▶ PROSODY EXTRACTOR (local, no LLM)                 │
    │               WPM · pause histogram · pitch variance ·       │
    │               energy variance · filler-token rate            │
    └───────────────────────────┬──────────────────────────────────┘
                                │
                    ┌───────────┴────────────┐
                    ▼                        ▼
        ┌───────────────────────┐  ┌─────────────────────────┐
        │ LIVE COACHING HUD     │  │ TURN-END DETECTOR       │
        │ (updates every 250ms) │  │ VAD silence ≥ threshold │
        │ no LLM in this path   │  │  + semantic completeness│
        │ ← THIS IS WHY IT'S    │  │  (small local model)    │
        │   FAST                │  └───────────┬─────────────┘
        └───────────────────────┘              │
                                               ▼
                          ┌────────────────────────────────────┐
                          │  ANSWER PIPELINE                   │
                          │                                    │
                          │  final transcript                  │
                          │    ↓                               │
                          │  domain classifier (fast/local)    │
                          │    ↓                               │
                          │  hybrid retrieval                  │
                          │   (candidate + JD + session)       │
                          │    ↓                               │
                          │  ┌──────────────┬───────────────┐  │
                          │  │ SCORER       │ FOLLOW-UP     │  │
                          │  │ rubric +     │ PLANNER       │  │
                          │  │ grounding    │ (graph-aware) │  │
                          │  └──────┬───────┴───────┬───────┘  │
                          │         │               │          │
                          │    stream to HUD   next question    │
                          └────────────────────────────────────┘
                                               │
                                               └──▶ loop to interviewer turn

2.4 Session state machine

Do not use a bag of booleans. One enum, one transition table, one audit log of transitions.

                    ┌──────┐
                    │ IDLE │
                    └───┬──┘
                        ▼
                 ┌──────────────┐
                 │ PREFLIGHT    │ device enum, permission probe,
                 └───┬──────────┘ provider ping, context warm
                     ▼
                 ┌──────────────┐
                 │ WARMING      │ load prep pack, prefetch embeddings,
                 └───┬──────────┘ open STT socket, warm TTS voice
                     ▼
                 ┌──────────────┐
              ┌─▶│ READY        │
              │  └───┬──────────┘
              │      ▼
              │  ┌─────────────────┐      barge-in
              │  │ INTERVIEWER_TURN│──────────────┐
              │  └───┬─────────────┘              │
              │      ▼                            ▼
              │  ┌─────────────────┐      ┌──────────────┐
              │  │ AWAITING_ANSWER │◀─────│ YIELDING     │
              │  └───┬─────────────┘      └──────────────┘
              │      ▼
              │  ┌─────────────────┐
              │  │ CANDIDATE_TURN  │ (streaming STT + live HUD)
              │  └───┬─────────────┘
              │      ▼
              │  ┌─────────────────┐
              │  │ TURN_END        │
              │  └───┬─────────────┘
              │      ▼
              │  ┌─────────────────┐
              │  │ SCORING         │ (async, non-blocking)
              │  └───┬─────────────┘
              │      ▼
              │  ┌─────────────────┐
              └──│ PLANNING_NEXT   │
                 └───┬─────────────┘
                     ▼
                 ┌──────────────┐
                 │ DEBRIEF      │
                 └──────────────┘

Error lattice (enterable from any state, with defined re-entry):
  DEGRADED_STT · DEGRADED_LLM · DEGRADED_TTS · RECONNECTING · PAUSED · FAILED · STOPPED

Every transition writes {from, to, reason, timestamp, session_id} to an in-memory ring buffer, dumped to session_state_log on completion. This is your single most valuable debugging artifact when a live demo misbehaves.

2.5 The Context Graph

Relational storage. Do not introduce a graph database. Postgres with proper indexes models this fine at portfolio and early-product scale, and adding Neo4j is a complexity signal that reads as inexperience, not sophistication.

Candidate ──has_skill──▶ Skill ◀──requires──── JDRequirement ──belongs_to──▶ Job
    │                      ▲                         │
    │                      │                         │
    ├──owns──▶ Project ──uses──┘                     │
    │             │                                  │
    │             ├──yielded──▶ Metric               │
    │             └──has──────▶ Story (STAR)         │
    │                              ▲                 │
    ├──has──▶ Experience           │                 │
    │                              │                 │
    └──ran──▶ Session ──asked──▶ Question ──targets──┘
                  │                  │
                  │                  ▼
                  └──produced──▶ Answer ──asserts──▶ Claim ──sourced_from──▶ DocumentChunk
                                    │
                                    └──scored_by──▶ RubricScore

Claim → DocumentChunk is the provenance edge. It is what makes the "click a claim, see the resume line it came from" demo possible, and it is the structural answer to "how do you prevent hallucination?"
