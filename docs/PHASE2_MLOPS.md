# PRAXIS InterviewOS — Phase 2 MLOps & Observability

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM N — OBSERVABILITY AND MLOPS  
**Classification**: PRODUCTION OPERATIONS SPECIFICATION  

---

## 1. Prompt Versioning & Boundary Enforcement

- **Strict File-Based Prompt Assets**:
  - All system prompts and rubric definitions are stored as versioned Markdown files under `prompts/` (e.g., `prompts/interviewer/system_v1.md`, `prompts/scoring/rubric_v1.md`, `prompts/classification/domain_v1.md`).
  - No ad-hoc, inline prompt strings are scattered across service layers.
  - Verified by `scripts/check_prompt_construction_boundary.py`.
- **Output Safety & Defense-in-Depth**:
  - `praxis_ai_gateway/output_safety.py`: Every structured output and text completion is scanned for system prompt leakage, delimiter escaping, and range validity before delivery.

---

## 2. Distributed Tracing & Telemetry

- **OpenTelemetry Instrumentation**:
  - Every AI gateway invocation creates a child span with attributes: `provider`, `model`, `task`, `method`, `latency_ms`, and `fell_back_from`.
  - Spans link to session and candidate contexts (`req_id`, `candidate_id`, `session_id`).
- **Structured JSON Logging**:
  - PII (emails, names) and API credentials are masked before writing to log streams (`backend/app/core/logging_config.py`).
