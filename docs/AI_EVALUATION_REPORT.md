# AI Evaluation Report

Offline and online evaluation results for PRAXIS AI features.
This report is regenerated on every model change and before any production promotion.

**Current evaluation status: STAGING** — no production traffic yet.
**Date:** 2026-10-05
**Evaluator:** AMIYA8597

---

## Evaluation framework

All offline evals run against the fixture data in `backend/tests/fixtures/eval/`.
Online evals are based on Cloud Run structured logs (`ai_call_log` table) once
staging receives real traffic.

### Grading scale

| Grade | Meaning |
|-------|---------|
| PASS | Meets the acceptance criterion |
| WARN | Acceptable but degraded; track over time |
| FAIL | Does not meet acceptance criterion; blocks promotion |
| BLOCKED | Cannot be measured without live infrastructure |

---

## 1. Session debrief quality

**Method:** 20 synthetic session transcripts with known correct diagnoses.
**Criterion:** ≥ 80% of deficiencies identified match the ground truth; no hallucinated
deficiencies in ≥ 90% of transcripts.

| Metric | Target | Result |
|--------|--------|--------|
| Deficiency recall | ≥ 80% | BLOCKED (no production data) |
| False positive rate | ≤ 10% | BLOCKED |
| `ServiceUnavailableError` on LLM failure | 100% | PASS (unit test) |

---

## 2. Hint ladder relevance

**Method:** 10 coding + 5 SQL + 5 system-design problems evaluated by rubric.
**Criterion:** Level-1 hint does not reveal the approach; level-3 hint is correct.

| Metric | Target | Result |
|--------|--------|--------|
| Level-1 non-reveal | 100% | BLOCKED |
| Level-3 correctness | ≥ 90% | BLOCKED |
| Fallback content on no gateway | returns non-empty string | PASS (unit test) |

---

## 3. Resume builder evidence grounding

**Method:** 5 synthetic candidate profiles + 5 JDs; verify all bullets cite real evidence IDs.
**Criterion:** 100% of bullets have a valid `evidence_source_id`; no invented metrics.

| Metric | Target | Result |
|--------|--------|--------|
| Evidence ID validity | 100% | PASS (server-side validation) |
| Fabricated metric rate | 0% | BLOCKED (human eval required) |
| Error on empty evidence | raises `ServiceUnavailableError` | PASS (unit test) |

---

## 4. OCR / screenshot classification

**Method:** 20 screenshot fixtures (coding, SQL, system-design, diagrams, general).
**Criterion:** ≥ 85% correct classification; no crash on any input.

| Metric | Target | Result |
|--------|--------|--------|
| Classification accuracy | ≥ 85% | BLOCKED (live fixtures needed) |
| Empty OCR handled | returns `system_design` | PASS (unit test) |
| VLM failure handled | returns fallback | PASS (unit test) |

---

## 5. JD analysis quality

**Method:** 10 real-world JD samples; verify extracted requirements vs. manually annotated.
**Criterion:** ≥ 75% requirement recall; seniority signal correct ≥ 90%.

| Metric | Target | Result |
|--------|--------|--------|
| Requirement recall | ≥ 75% | BLOCKED |
| Seniority accuracy | ≥ 90% | BLOCKED |
| ARQ retry on transient failure | ≤ 3 retries before dead-letter | PASS (unit test) |

---

## 6. Embedding retrieval quality

See `docs/RAG_EVALUATION_REPORT.md` for dedicated RAG evaluation.

---

## Overall promotion status

| Environment | Status |
|-------------|--------|
| Staging | READY FOR STAGING (unit/integration tests PASS; offline evals BLOCKED pending live data) |
| Production | NOT READY (requires staging traffic + human eval sign-off) |

---

## BLOCKED items (require live infrastructure)

All offline human-eval metrics above require:
1. Supabase PostgreSQL (BLOCKED — provisioning required).
2. Real LLM provider keys in GCP Secret Manager (BLOCKED).
3. At least one week of staging traffic to populate `ai_call_log`.
