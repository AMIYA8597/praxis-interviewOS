# PRAXIS InterviewOS — Phase 2 Cost Analysis & Budget Controls

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM L — MODEL AND PROVIDER ORCHESTRATION  
**Classification**: FINANCIAL ENGINEERING SPECIFICATION  

---

## 1. Zero-Spend & Free-Tier Guardrails

PRAXIS provides deterministic, hard enforcement against runaway AI provider bills:

1. **`ZERO_SPEND_MODE=true`**:
   - Any request attempting to call a billable cloud provider is rejected before network dispatch.
   - Forces routing strictly through zero-cost pathways (local Ollama / Piper / Silero or generous free tiers).
2. **`FREE_TIER_BUDGET_DAILY_USD=$0.50`**:
   - Redis-backed atomic token and cost counter tracks candidate spend per UTC calendar day.
   - When spend reaches budget limit, non-free providers are automatically disabled for that candidate.
3. **Explicit User Consent for Paid Tiers**:
   - `budget_guard.check_consent(user_id)` requires explicit database flag `allow_paid_models = true` before routing to OpenAI or Anthropic.

---

## 2. Unit Economics Per 30-Minute Mock Interview Session

Assumes typical 30-minute interview: 10 conversational turns, ~1,500 candidate words spoken, 10 answers scored, 1 comprehensive debrief:

| Architecture Profile | STT Cost | LLM Reasoning Cost | Evaluation & Debrief Cost | Total Session Cost |
|---|---|---|---|---|
| **100% Sovereign Local** (Ollama + faster-whisper + Piper) | $0.00 | $0.00 | $0.00 | **$0.00** |
| **Hybrid Free-Tier** (Groq llama-3.3 + faster-whisper) | $0.00 | $0.00 | $0.00 | **$0.00** |
| **Production Cloud Tier** (faster-whisper + GPT-4o-mini / GPT-4o) | $0.00 | $0.02 | $0.07 | **$0.09** |
| **Premium High-Fidelity** (Claude 3.5 Sonnet + Deepgram) | $0.04 | $0.05 | $0.12 | **$0.21** |
