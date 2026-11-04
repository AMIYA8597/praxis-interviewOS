# PRAXIS InterviewOS — AI Usage, Token Accounting & Budget Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Token Consumption & Cost Guardrails

1. **Hard Budget Ceilings:**
   - Per-Session Token Limit: 4,000 tokens (input + output).
   - Per-User Daily Budget Limit: $1.00 USD.
   - Enforced by `praxis_ai_gateway.budget.BudgetGuard` with atomic increments in Redis and PostgreSQL persistence.
2. **Dynamic Cost Tracking:**
   - Every completed LLM call records:
     - Prompt tokens
     - Completion tokens
     - Effective cost in USD (calculated from pricing metadata in `config/models.yaml`)
     - Latency in milliseconds
     - Provider and exact model ID

---

## 2. Average Token Usage per Interview

| Stage | Input Tokens | Output Tokens | Model Used | Estimated Cost (Blended) |
|---|---|---|---|---|
| **Question Generation** | ~800 | ~150 | Groq `llama-3.3-70b` / Gemini `gemini-2.5-flash-lite` | $0.0000 |
| **Spoken Turn Evaluation (x5)** | ~500 each (~2,500) | ~200 each (~1,000) | Gemini `gemini-2.5-flash-lite` / `gemini-3.5-flash` | $0.0000 |
| **Post-Session Debrief** | ~2,000 | ~800 | Groq `llama-3.3-70b` / OpenAI `gpt-4o-mini` | ~$0.0012 |
| **Total per 30-min Interview** | **~5,300 tokens** | **~1,950 tokens** | — | **< $0.002 / interview** |
