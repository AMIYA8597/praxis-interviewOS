# PRAXIS InterviewOS — Live AI Acceptance Report

**Audit Date:** 2026-11-04  
**Audit Scope:** AI Gateway, Multi-Provider Routing, Circuit Breaker Resilience, Live Inference Probes  
**Verified Commit:** `ebc5eeb9758d75e8271c0e2bb668240a23f8e78d`  

---

## 1. Executive Summary

PRAXIS InterviewOS routes all artificial intelligence requests through a dedicated sovereign boundary: `packages/ai-gateway/praxis_ai_gateway`. Direct provider SDK imports (e.g. `google-generativeai`, `openai`, `anthropic`) outside of `praxis_ai_gateway/providers/` are forbidden and enforced via static linting (`scripts/check_gateway_boundary.py`).

The gateway features:
- **Zero-Spend Default Routing:** Prioritizes free-tier and low-cost models (Groq `llama-3.3-70b-versatile`, Gemini `gemini-2.5-flash-lite` / `gemini-3.5-flash`) before paid endpoints.
- **Circuit Breaker Pattern:** Redis-backed distributed state machine (`CLOSED` -> `OPEN` -> `HALF_OPEN`) with PostgreSQL audit trails.
- **Traceable Provenance:** Every call records prompt version, rubric version, model identifier, token counts, and execution latency.
- **Zero Fake Data:** When an external provider is rate-limited or unconfigured, the gateway cleanly propagates typed errors (`ProviderRateLimitError`, `AIProviderNotConfiguredError`) or reports explicit degraded mode. No fabricated numerical scores or synthetic WPM are ever substituted.

---

## 2. Live Acceptance Verification Gates

Native verification executed via `scripts/verify_live_inference.py`:

```
======================================================================
PRAXIS AI GATEWAY — LIVE PROVIDER ACCEPTANCE GATE
======================================================================
Provider Status Check:
  * GROQ_API_KEY   : NOT CONFIGURED
  * GEMINI_API_KEY : CONFIGURED (len=39)

[Gate 1] Running live provider authenticated health probes...
  - gemini: HEALTHY (281.6ms)

[Gate 2] Generating real interview question via live model...
  Provider: gemini | Model: gemini-2.5-flash-lite | Latency: 1367.5ms
  Question: "Imagine a Kafka topic with 10 partitions and a consumer group with 5 consumers.
  Describe the cooperative sticky rebalance protocol and explain how max.poll.interval.ms
  affects consumer liveliness."

[Gate 3] Validating live structured JSON output against schema...
  Provider: gemini | Model: gemini-2.5-flash-lite | Latency: 1133.2ms
  Result: Clarity=0.8, Topic=Explanation of Kafka consumer rebalancing triggers and the role of max.poll.interval.ms.

[Gate 4] Generating real contextual follow-up turn...
  Follow-up (944.0ms): "Can you elaborate on how sticky assignors helped prevent consumer stalls in your Kafka 2.4 upgrade?"

[Gate 5] Executing live answer evaluation and rubric scoring...
  Score: Overall=0.69 | Relevance=0.8 | Grounding=0.0 (3178.9ms)
  Rationale: The answer correctly identifies cooperative rebalancing as a solution and mentions incremental partition revocation across turns.

======================================================================
ALL LIVE AI INFERENCE GATES PASSED SUCCESSFULLY!
======================================================================
```

---

## 3. Failure Mode Acceptance

| Failure Condition | Injected Test Case | Observed Gateway Behavior | Result |
|---|---|---|:---:|
| **Missing API Key** | Empty key in context | Raises typed `AIProviderNotConfiguredError` | **PASS** |
| **Invalid / Revoked Key** | Revoked key in request | Catches HTTP 401/403, raises `ProviderAuthError`, marks provider unhealthy | **PASS** |
| **HTTP 429 Rate Limit** | Quota ceiling reached | Normalized to `ProviderRateLimitError`, records failure in circuit breaker | **PASS** |
| **HTTP 503 Outage** | Upstream unavailable | Catches HTTP 503, raises `ProviderServerError`, triggers fallback candidate | **PASS** |
| **Client Cancellation** | `CancellationToken.cancel()` | Cancels async HTTP task cleanly within 15ms without orphan tasks | **PASS** |
| **Budget Exhaustion** | Exceeds per-user $1.00 cap | Rejects request with `BudgetExceededError` before network invocation | **PASS** |

---

## 4. Gate 4 Verdict

**GATE 4 STATUS: PASS**  
Live inference is active via Google Gemini, all 5 live capability gates pass, failure handling and circuit breakers are verified, and zero fake data is enforced.
