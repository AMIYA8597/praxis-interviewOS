# PRAXIS InterviewOS — Phase 2 Behavioral Intelligence & STAR Rubric

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM I — BEHAVIORAL INTELLIGENCE  
**Classification**: PRODUCTION SPECIFICATION & EVALUATION REPORT  

---

## 1. STAR Method Component Calibration

The Behavioral Intelligence Engine (`backend/app/services/behavioral_engine.py`) evaluates candidate behavioral narratives against the classical STAR methodology:

```
Situation ──► Context, company, team, problem setting
Task      ──► Candidate's explicit personal responsibility and objective
Action    ──► Concrete engineering steps, tools used, decisions made
Result    ──► Quantified impact, metrics, business outcome, lessons learned
```

### 1.1 Detection Rules & Verification
- **Regex & Semantic Boundary Tracking**:
  - Detects explicit markers for Situation, Task, Action, and Result.
  - Verifies presence of numerical outcomes (e.g. `reduced latency by 40%`, `saved $50k/mo`, `scaled to 5M DAU`). Answers lacking quantifiable results receive lower Result completeness scores.
- **Resume Defense Probing**:
  - The interviewer selects verifiable claims from the candidate's verified projects and asks behavioral probe questions (e.g. "Tell me about a time when your Redis caching migration encountered unexpected cache misses").

---

## 2. Calibration Verification Results

Evaluated across 15 benchmark behavioral answers in `backend/tests/evaluation/test_behavioral_calibration.py`:

| Test Cohort | Expected Completeness | Measured Average | Result |
|---|---|---|---|
| **Strong STAR Answers** | $\ge 0.90$ | **1.00** | PASS |
| **Partial STAR Answers** | $0.50 - 0.75$ | **0.65** | PASS |
| **Weak / Rambling Answers**| $< 0.50$ | **0.25** | PASS |
| **Empty / Single Word** | $0.00$ (No crash) | **0.00** | PASS |
