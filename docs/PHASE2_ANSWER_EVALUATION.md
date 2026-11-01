# PRAXIS InterviewOS — Phase 2 Answer Evaluation Engine

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM E — ANSWER EVALUATION ENGINE  
**Classification**: PRODUCTION SPECIFICATION & RUBRIC CONTRACT  

---

## 1. Multi-Dimensional Rubric Architecture

Answer scoring (`realtime_agent/app/scoring/service.py`) evaluates candidate spoken answers across structured dimensions on a calibrated $[0.0, 1.0]$ continuous scale:

| Dimension | Weight | Description | Evaluation Basis |
|---|---|---|---|
| **Correctness** | 0.30 | Technical accuracy and conceptual validity | Evaluated against domain knowledge base |
| **Relevance** | 0.20 | Directness in addressing the interviewer's question | Semantic alignment with question intent |
| **Specificity** | 0.20 | Depth of concrete examples, metrics, and implementation specifics | Ratio of technical entities & quantified metrics |
| **Structure** | 0.10 | Logical flow, coherent argument, executive clarity | Topic sentences, clear transitions, structured cadence |
| **Grounding** | 0.10 | Consistency with verified candidate background documents | Ratio of verified claims to total factual claims made |
| **Conciseness** | 0.10 | Economy of language, absence of rambling | Word count relative to information density |

---

## 2. Calibrated Scoring & Uncertainty Principles

- **No Fabricated Zeros**:
  - If a dimension cannot be evaluated (e.g. STT degraded, provider timeout, or unanswerable prompt), the score is stored as `null` with `measurement_status="UNAVAILABLE"` or `"DEGRADED"`.
- **Determinism**:
  - The overall score is computed deterministically in Python via the weighted formula:
    $$\text{Overall} = \sum_{d \in \text{dimensions}} w_d \cdot \text{score}_d$$
  - The LLM does not invent an arbitrary overall score; it scores individual dimensions, and the application aggregates them according to validated mathematical weights.
- **Human-Reviewed Calibration**:
  - Verified across 6 canonical answer archetypes: correct technical, incorrect technical, overly short, hallucinated claims, strong STAR behavioral, and weak STAR behavioral.
