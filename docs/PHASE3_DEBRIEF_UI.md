# PRAXIS InterviewOS — Phase 3 Debrief & AI Feedback Experience

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: EVALUATION UI SPECIFICATION  

---

## 1. Debrief Overview & Structure

The Debrief page (`/sessions/[id]/debrief`) transforms raw interview audio and turn transcripts into actionable, structured feedback.

### Key Sections:
1. **Headline Metrics**: Average speaking pace (WPM), filler word rate (%), overall evaluation score (/100).
2. **Multi-Dimensional Rubric (`ScoreDisplay`)**:
   - Relevance (15%)
   - Technical Correctness (25%)
   - Structure & Delivery (15%)
   - Specificity & Detail (15%)
   - Evidence Grounding (20%)
   - Conciseness & Clarity (10%)
3. **STAR Method Coverage**: Transparent visual flags confirming whether Situation, Task, Action, and Result were addressed in behavioral answers.
4. **5-Tier Claim Grounding (`EvidenceReference`)**: Visual audit trail mapping candidate spoken assertions against verified document excerpts.
5. **Turn-by-Turn Transcript**: Full conversational dialogue with timestamping and speaker attribution.

---

## 2. 5-Tier Evidence Classification Scheme

| Status | Badge Label | Theme | Meaning |
| :--- | :--- | :--- | :--- |
| `SUPPORTED` | Verified Fact | Emerald Green | The statement is directly corroborated by resume or project code. |
| `PARTIALLY_SUPPORTED` | Partially Supported | Amber Yellow | The claim contains minor discrepancies or unverified metric precision. |
| `UNSUPPORTED` | Unverified | Slate Gray | The claim is not documented in provided candidate files. |
| `CONTRADICTED` | Contradicted | Rose Red | The assertion directly conflicts with documented experience. |
| `UNCERTAIN` | Needs Clarification | Indigo Blue | Ambiguous claim requiring follow-up questioning. |

---

## 3. Honest Measurement Transparency

- When all AI evaluation pipelines succeed: `measurement_status = MEASURED`.
- When evaluation used text fallback only: `measurement_status = ESTIMATED`.
- When speech processing or audio signals were impaired: `measurement_status = DEGRADED`.
- When evaluation failed or could not execute: `measurement_status = UNAVAILABLE` (scores rendered as `N/A`, never fake zeros or synthetic defaults).
