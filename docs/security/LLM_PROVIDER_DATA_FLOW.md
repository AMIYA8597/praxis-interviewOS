# PRAXIS InterviewOS — LLM Provider Data Flow & Privacy Governance

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: PRIVACY & THIRD-PARTY DATA FLOW SPECIFICATION  

---

## 1. Third-Party Provider Topology

The PRAXIS AI Gateway routes model inferences across authorized providers:
- **OpenAI** (`api.openai.com`)
- **OpenRouter** (`openrouter.ai`)
- **DeepSeek** (via OpenRouter or direct endpoint)
- **Google Gemini** (`generativelanguage.googleapis.com`)
- **Self-Hosted Ollama** (local/on-premise offline fallback)

---

## 2. Data Flow Invariants & PII Minimization

```
[ Candidate Career Input ]
            |
            v
[ PII Sanitization Pass ]
  - Strips personal phone numbers, physical addresses, and candidate email.
  - Retains strictly professional project skills, architecture descriptions, and metrics.
            |
            v
[ Server-Side Key Injection ]
  - Provider API keys (OPENAI_API_KEY, GOOGLE_API_KEY) are injected inside
    the backend container environment.
  - Keys are NEVER exposed to client browsers or mobile devices.
            |
            v
[ External API Transmission (HTTPS TLS 1.3) ]
  - Custom base URLs must pass is_safe_url() SSRF checks.
  - Requests set zero-retention flags where supported (e.g. OpenAI zero-data-retention agreements).
            |
            v
[ Structured Output Parsing & Scrubbing ]
  - Completes rubric evaluation; responses scrubbed for sensitive tokens before storage.
```

---

## 3. Provider Data Retention Status
- **OpenAI API**: Under commercial API terms, data sent via the API is not used to train models and is retained for a maximum of 30 days for abuse monitoring unless zero-data retention (ZDR) is configured.
- **Google Gemini API**: Paid tier enterprise enterprise agreements disallow training on user prompt data.
- **DeepSeek / OpenRouter**: Routed strictly via enterprise endpoints subject to standard API privacy contracts.
