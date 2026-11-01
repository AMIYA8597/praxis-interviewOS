# PRAXIS InterviewOS — Phase 2 Model Selection & Provider Routing

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM L — MODEL AND PROVIDER ORCHESTRATION  
**Classification**: ARCHITECTURE CONFIGURATION SPECIFICATION  

---

## 1. Provider Routing & Capability Matrix

All model interactions flow through the centralized AI Gateway (`packages/ai-gateway/praxis_ai_gateway/router.py`). Direct provider SDK calls outside the gateway are strictly prohibited and verified by `scripts/check_gateway_boundary.py`.

| Task Alias | Primary Provider & Model | Cloud Fallback | Local Fallback | Max Latency SLA |
|---|---|---|---|---|
| `fast_classify` | Groq `llama-3.1-8b-instant` | OpenAI `gpt-4o-mini` | Ollama `llama3.1:8b` | 1000 ms |
| `reasoning` | Groq `llama-3.3-70b-versatile` | OpenAI `gpt-4o-mini` | Ollama `llama3.1:8b` | 10000 ms |
| `deep_reasoning` | OpenAI `gpt-4o` | Anthropic `claude-3-5-sonnet` | Groq `llama-3.3-70b` | 10000 ms |
| `stt_stream` | `faster-whisper` (small.en / tiny.en) | Groq Whisper / Deepgram | — | 1500 ms |
| `tts_stream` | `Piper TTS` (en_US-lessac-low) | Edge-TTS / ElevenLabs | — | 500 ms |
| `embedding` | Local `BAAI/bge-small-en-v1.5` | — | Local HuggingFace | 250 ms |
| `question_generation` | Groq `llama-3.3-70b-versatile` | OpenAI `gpt-4o-mini` | Ollama `llama3.1:8b` | 5000 ms |
| `answer_evaluation` | OpenAI `gpt-4o` | Anthropic `claude-3-5-sonnet` | Groq `llama-3.3-70b` | 10000 ms |
| `claim_grounding` | Groq `llama-3.3-70b-versatile` | OpenAI `gpt-4o-mini` | Ollama `llama3.1:8b` | 5000 ms |
| `debrief_generation` | OpenAI `gpt-4o` | Anthropic `claude-3-5-sonnet` | Groq `llama-3.3-70b` | 15000 ms |

---

## 2. Resiliency & Circuit Breakers

- **Circuit Breaker**: Redis-backed state machine (Closed -> Open -> Half-Open). 3 consecutive errors trip the breaker for 30s, automatically diverting subsequent requests to the fallback provider without thread blocking.
- **Cancellation Propagation**: If the candidate speaks while a generation task is running (barge-in), the `CancellationToken` signals the gateway adapter, immediately terminating network streaming and freeing worker capacity.
