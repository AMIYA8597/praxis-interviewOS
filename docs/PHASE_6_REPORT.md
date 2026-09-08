# Phase 6 Implementation Report

**Phase:** 6 - Model Registry & Startup Validation  
**Objective:** Decouple hardcoded model IDs from the business logic into a central YAML registry, and establish a strict startup validation guard to enforce API documentation checks.

## Implemented
- **Central Model Registry:** Created `config/models.yaml` establishing the tier aliases (`fast_classify`, `reasoning`, `vision`, `embedding`, `stt_stream`, `tts`) mapped to their fallback local and cloud models.
- **Intentional Sabotage Placeholder:** Explicitly implemented the `<VERIFY_AT_BUILD>` placeholders in `models.yaml`.
- **Startup Validator Guard:** Built `backend/app/core/validator.py` using PyYAML. This script dynamically parses the `models.yaml` tree during the FastAPI `@app.on_event("startup")` lifecycle hook.
- **Fail-Fast Crash:** If any provider configuration retains the literal `<VERIFY_AT_BUILD>` string, the application immediately aborts with a `ConfigurationError`, explicitly forcing the developer to perform the verification protocol before the environment can boot.

## Files Changed
- `config/models.yaml` (New)
- `backend/app/core/validator.py` (New)
- `backend/app/main.py`

## Database Changes
- None this sprint.

## API Changes
- None.

## AI Changes
- Hardcoded IDs are eradicated from the Python source, preparing for fluid fallback orchestration in later iterations.

## Next phase
- **Phase 7 — Telemetry & Diagnostics** (Optional / Up to Spec).
