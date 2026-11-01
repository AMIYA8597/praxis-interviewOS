# PRAXIS InterviewOS — Rate Limiting, Abuse Prevention & Availability Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: AVAILABILITY & ABUSE PREVENTION SPECIFICATION  

---

## 1. Multi-Tiered Rate Limiting Strategy

To defend against distributed denial-of-service (DDoS), credential stuffing, and expensive AI inference exhaustion, PRAXIS implements tiered rate limits:

```
[ Tier 1: IP-Based Edge Limits ]
  - Protects unauthenticated endpoints (login, password reset)
  - 10 login attempts / minute per IP (prevents brute-force)
  - 120 general requests / minute per IP

[ Tier 2: Account & Candidate Scoped Limits ]
  - Protects authenticated resource-heavy operations
  - 10 resume document uploads / hour per candidate
  - 20 practice session initializations / hour per candidate
  - 60 turn evaluations / minute per active session

[ Tier 3: Realtime Frame Rate Limits ]
  - Protects WebSocket audio workers
  - Audio chunk intervals clamped to ~250ms (4 frames/sec @ 16kHz)
  - Max payload 1MB per frame; drops anomalous burst floods
```

---

## 2. Circuit Breakers & Resource Budgeting

1. **AI Gateway Circuit Breakers**:
   - `packages/ai-gateway/praxis_ai_gateway/resilience.py` tracks rolling 60-second provider failure rates.
   - If a provider triggers >= 5 consecutive 5xx errors or timeouts, the circuit opens for 30 seconds, automatically failing over to the backup model (e.g. falling back from OpenAI to Gemini or local Ollama).
2. **Monthly Token Budget Guards**:
   - `packages/ai-gateway/praxis_ai_gateway/budget.py` tracks estimated token costs per candidate and globally.
   - Prevents unexpected bill spikes or financial exhaustion attacks.
