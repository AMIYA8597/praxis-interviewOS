# AI Risk Register

Identifies, quantifies, and tracks risks arising from AI/ML components in PRAXIS.
Updated whenever a new model is added, a new prompt path is introduced, or a new
AI-powered feature ships.

Last reviewed: 2026-10-05 | Reviewer: AMIYA8597

---

## Severity scale

| Level | Definition |
|-------|-----------|
| **Critical** | Directly causes user harm, legal liability, or data breach |
| **High** | Degrades core product value significantly; likely visible to users |
| **Medium** | Degrades quality; manageable degradation mode exists |
| **Low** | Cosmetic or edge-case; acceptable degradation |

---

## Risk register

### R-001 — Hallucinated resume bullets

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Medium |
| **Component** | `resume_builder.py`, `POST /api/v1/resumes/tailored` |
| **Description** | LLM invents achievements, metrics, or technologies not present in the candidate's evidence. |
| **Mitigation (implemented)** | `PromptBuilder.add_untrusted()` tags evidence as externally-sourced. System prompt forbids fabrication. Every bullet requires `evidence_source_id`. Code validates that returned `evidence_source_id` was drawn from the provided list. |
| **Residual risk** | LLM may paraphrase in misleading ways even when grounded. |
| **Detection** | `evidence_source_id` references validated server-side; any missing ID raises `ServiceUnavailableError`. |
| **Owner** | Backend |

### R-002 — Prompt injection via JD / resume upload

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Low–Medium |
| **Component** | All LLM call sites that process user-uploaded documents (`analyze_job`, `process_resume`, `resume_builder`) |
| **Description** | Adversarially crafted job description or resume text manipulates LLM to exfiltrate data or override instructions. |
| **Mitigation (implemented)** | `PromptBuilder.add_untrusted(label, source, text)` wraps every user document in a clearly-delimited XML block; system prompt instructs the model to treat content of that block as opaque data, not instructions. |
| **Residual risk** | No prompt injection defense is perfect against adaptive adversaries. |
| **Detection** | No runtime detection. Logged for manual review on abuse reports. |
| **Owner** | AI Gateway |

### R-003 — AI-assisted cheating on live employer interviews

| Field | Value |
|-------|-------|
| **Severity** | **Critical** |
| **Likelihood** | By design: blocked |
| **Component** | Entire platform |
| **Description** | PRAXIS functionality used covertly to answer questions during a real employer interview. |
| **Mitigation (implemented)** | **This use case is explicitly forbidden** in the system prompt of every coaching endpoint. All sessions are branded as "practice". No "stealth" mode exists. No endpoint accepts screenshots from a user-indicated live interview context without explicit consent and PRAXIS-aware framing. |
| **Residual risk** | Cannot prevent all off-label use by determined users. |
| **Detection** | Rate limiting. No feature deliberately enables or optimises for undetected use. |
| **Owner** | Product + Legal |

### R-004 — OCR/VLM misclassification of screenshot

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Component** | `vision_pipeline.py`, `POST /api/v1/study/screenshot` |
| **Description** | Screenshot of a coding problem is classified as system_design; user receives wrong coaching. |
| **Mitigation (implemented)** | Regex-based fast-path for obvious code markers before VLM call. VLM call with structured output schema. Users can retry or provide text directly. |
| **Residual risk** | Low-resolution or unusual-font screenshots will still misclassify. |
| **Detection** | Session feedback ratings surfaced to analytics. |
| **Owner** | Backend |

### R-005 — Embedding model mismatch after update

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Low (only on manual model swap) |
| **Component** | `pgvector` HNSW index, `document_processing.py` |
| **Description** | If the embedding model is changed to one with different dimensions or normalisation, all existing embeddings become incomparable. |
| **Mitigation (implemented)** | Model is baked into Docker image and `HF_HUB_OFFLINE=1`. Changing the model requires a new image build. `config/models.yaml` declares the expected embedding dimension; `document_processing.py` asserts at startup. |
| **Residual risk** | A silent drift in model quantisation could go undetected. |
| **Detection** | Startup assertion + retrieval quality monitoring via `docs/RAG_EVALUATION_REPORT.md`. |
| **Owner** | ML / Backend |

### R-006 — LLM provider outage degrades core flows

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Component** | AI gateway, all LLM-dependent endpoints |
| **Description** | Provider API outage makes hint generation, debrief, JD analysis, and resume builder unavailable. |
| **Mitigation (implemented)** | Gateway retries with exponential backoff. All LLM-dependent services have explicit fallback paths (domain-generic hints, "service temporarily unavailable" errors — never fabricated data). ARQ worker retries transient failures. |
| **Residual risk** | Extended outage (>1h) causes degraded experience. |
| **Detection** | `check_provider_health` cron job + Cloud Monitoring alerts. |
| **Owner** | Infrastructure |

### R-007 — Semantic search returns irrelevant or private content

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Low (mitigated by RLS) |
| **Component** | `document_chunks` pgvector HNSW retrieval, `GET /api/v1/memory/search` |
| **Description** | User A's document chunks returned in User B's semantic search. |
| **Mitigation (implemented)** | Row-Level Security (RLS) + FORCE ROW LEVEL SECURITY on `document_chunks`. JWT claims propagated via `set_config('request.jwt.claims', ...)` before every query. Candidate-scoped `candidate_id` filter on every retrieval query. |
| **Residual risk** | Misconfiguration of `request.jwt.claims` in a worker context. |
| **Detection** | Integration tests assert cross-tenant isolation. |
| **Owner** | Backend / Security |

### R-008 — AI scoring presents fake accuracy

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Likelihood** | Blocked by policy |
| **Component** | All scoring/debrief endpoints |
| **Description** | Backend returns fabricated "85% accuracy" or hardcoded session scores. |
| **Mitigation (implemented)** | **Policy: mocks are allowed ONLY inside automated tests/fixtures.** No hardcoded metrics in runtime paths. Debrief service returns `ServiceUnavailableError` on LLM failure, not a fake score. Tests verify service raises on gateway failure. |
| **Residual risk** | None — enforced by code review policy. |
| **Owner** | Backend |

---

## Monitoring and review cadence

| Frequency | Action |
|-----------|--------|
| Every model change | Re-run AI evaluation report; update R-005 |
| Monthly | Review AI call log anomalies; verify fallback rates |
| Quarterly | Full risk register review |
| On abuse report | Ad-hoc review of R-002, R-003 |
