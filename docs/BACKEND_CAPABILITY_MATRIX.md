# PRAXIS Backend Capability Matrix

Legend:
- `✓` — Yes / confirmed in codebase
- `!` — Partial / scaffolded but incomplete
- `-` — No / not present / unknown

STAGING_VERIFIED and PRODUCTION_VERIFIED are `-` throughout: GCP infrastructure has not
been provisioned and no cloud deployment has been executed.

| Category | Capability | IMPLEMENTED | INTEGRATED | TESTED | STAGING_VERIFIED | PRODUCTION_VERIFIED |
|---|---|---|---|---|---|---|
| **AUTH** | JWT_VERIFICATION | ✓ | ✓ | ✓ | - | - |
| | SIGNUP | - | - | - | - | - |
| | LOGIN | - | - | - | - | - |
| | LOGOUT | ✓ | ✓ | ! | - | - |
| | REFRESH | - | - | - | - | - |
| | SESSION_VALIDATION | ✓ | ✓ | ✓ | - | - |
| **AUTHZ** | OWNERSHIP_CHECKS | ✓ | ✓ | ✓ | - | - |
| | ADMIN_ROLE | ✓ | ✓ | ✓ | - | - |
| | RLS_ENFORCEMENT | ✓ | ✓ | ✓ | - | - |
| | FORCE_RLS | ✓ | ✓ | ✓ | - | - |
| **DATABASE** | MIGRATIONS | ✓ | ✓ | ✓ | - | - |
| | CONNECTION_POOLING | ✓ | ✓ | ! | - | - |
| | CONSTRAINTS | ✓ | ✓ | ✓ | - | - |
| | INDEXES | ✓ | ✓ | ! | - | - |
| | PGVECTOR | ✓ | ✓ | ✓ | - | - |
| **STORAGE** | UPLOAD_VALIDATION | ✓ | ✓ | ! | - | - |
| | MIME_CHECK | ✓ | ✓ | ! | - | - |
| | PRIVATE_BUCKET | ✓ | ! | ! | - | - |
| | SIGNED_URLS | ! | ! | - | - | - |
| | DELETION | ✓ | ✓ | ! | - | - |
| **RESUME_AI** | PARSING | ✓ | ✓ | ✓ | - | - |
| | CHUNKING | ✓ | ✓ | ✓ | - | - |
| | EMBEDDINGS | ✓ | ✓ | ✓ | - | - |
| | SKILL_EXTRACTION | ✓ | ✓ | ! | - | - |
| | CLAIM_EXTRACTION | ✓ | ✓ | ! | - | - |
| **JD_AI** | PARSING | ✓ | ✓ | ✓ | - | - |
| | REQUIREMENT_EXTRACTION | ✓ | ✓ | ✓ | - | - |
| | SKILL_MAPPING | ✓ | ✓ | ! | - | - |
| | WEIGHT_ASSIGNMENT | ! | ! | - | - | - |
| **RAG** | VECTOR_SEARCH | ✓ | ✓ | ! | - | - |
| | LEXICAL_SEARCH | ✓ | ✓ | ! | - | - |
| | HYBRID_RERANKING | ! | ! | - | - | - |
| | CROSS_TENANT_ISOLATION | ✓ | ✓ | ✓ | - | - |
| **VAD** | SILERO_ONNX | ✓ | ✓ | ! | - | - |
| | STATE_MACHINE | ✓ | ✓ | ! | - | - |
| | CONFIGURABLE_THRESHOLDS | ! | ! | - | - | - |
| **STT** | LOCAL_FASTER_WHISPER | ✓ | ✓ | ! | - | - |
| | CLOUD_GROQ_FALLBACK | ✓ | ✓ | ! | - | - |
| | STREAMING_PARTIAL | ✓ | ✓ | ! | - | - |
| | RECONNECT | ✓ | ! | - | - | - |
| **TTS** | PIPER_LOCAL | ✓ | ! | - | - | - |
| | STREAMING | ✓ | ! | - | - | - |
| | CANCELLABLE | ✓ | ! | - | - | - |
| | BARGE_IN | ! | ! | - | - | - |
| **LLM** | STRUCTURED_OUTPUT | ✓ | ✓ | ✓ | - | - |
| | PROMPT_VERSIONING | ! | ! | - | - | - |
| | RETRY_ON_VALIDATION_FAIL | ✓ | ✓ | ! | - | - |
| **AI_GATEWAY** | PROVIDER_ISOLATION | ✓ | ✓ | ✓ | - | - |
| | BUDGET_GUARD | ✓ | ✓ | ✓ | - | - |
| | CIRCUIT_BREAKER | ✓ | ✓ | ! | - | - |
| | FALLBACK_CHAIN | ✓ | ✓ | ✓ | - | - |
| | OUTPUT_SAFETY | ✓ | ✓ | ✓ | - | - |
| **INTERVIEWER** | ADAPTIVE_DIFFICULTY | ✓ | ! | - | - | - |
| | QUESTION_BANK | ✓ | ✓ | ! | - | - |
| | FOLLOW_UPS | ✓ | ✓ | ! | - | - |
| | STATE_MACHINE | ✓ | ✓ | ! | - | - |
| **TECHNICAL_SCORING** | CORRECTNESS | ✓ | ✓ | ! | - | - |
| | DEPTH | ✓ | ✓ | ! | - | - |
| | EVIDENCE | ✓ | ✓ | ! | - | - |
| | RUBRIC_VERSION | ✓ | ✓ | ✓ | - | - |
| **SYSTEM_DESIGN** | 24_PHASE_FLOW | ✓ | ! | - | - | - |
| | CONTRADICTION_DETECTION | ✓ | ! | - | - | - |
| | DYNAMIC_CHALLENGES | ! | - | - | - | - |
| **CODING** | SANDBOXED_EXECUTION | ! | ! | - | - | - |
| | RESOURCE_LIMITS | ! | ! | - | - | - |
| | HIDDEN_TESTS | - | - | - | - | - |
| **BEHAVIORAL** | STAR_DETECTION | ✓ | ✓ | ✓ | - | - |
| | PER_COMPONENT_SCORING | ✓ | ✓ | ✓ | - | - |
| | OWNERSHIP_METRICS | ! | ! | - | - | - |
| **GROUNDING** | SUPPORTED_PARTIALLY_UNSUPPORTED_CONTRADICTED | ✓ | ✓ | ! | - | - |
| | EVIDENCE_REQUIRED | ✓ | ✓ | ! | - | - |
| **READINESS** | MULTI_DIMENSION | ✓ | ✓ | ! | - | - |
| | CONFIDENCE | ✓ | ✓ | ! | - | - |
| | SAMPLE_COUNT | ✓ | ✓ | ! | - | - |
| | NO_HIRE_PROBABILITY | ! | - | - | - | - |
| **STUDY** | SM2_ALGORITHM | ✓ | ✓ | ✓ | - | - |
| | KNOWLEDGE_DECAY_DETECTION | ! | ! | - | - | - |
| | INTERVIEW_EXPRESSION_GAP | ! | ! | - | - | - |
| **ANALYTICS** | SESSION_COMPARISON | ✓ | ✓ | ! | - | - |
| | TREND_TRACKING | ✓ | ✓ | ! | - | - |
| | JD_COVERAGE | ✓ | ✓ | ! | - | - |
| **REALTIME** | WEBSOCKET_AUTH | ✓ | ✓ | ! | - | - |
| | SESSION_RESUME_ON_RECONNECT | ✓ | ! | - | - | - |
| | REDIS_STATE | ✓ | ✓ | ! | - | - |
| **WORKERS** | ARQ_POOL | ✓ | ✓ | ✓ | - | - |
| | RETRY_BACKOFF | ✓ | ✓ | ✓ | - | - |
| | DEAD_LETTER | ✓ | ✓ | ✓ | - | - |
| | IDEMPOTENCY | ✓ | ✓ | ! | - | - |
| | GRACEFUL_SHUTDOWN | ✓ | ✓ | ! | - | - |
| **SECURITY** | PROMPT_INJECTION_DEFENCE | ✓ | ✓ | ✓ | - | - |
| | UPLOAD_SECURITY | ✓ | ✓ | ! | - | - |
| | SSRF_GUARD | ✓ | ✓ | ! | - | - |
| | AUDIT_LOG | ✓ | ✓ | ! | - | - |
| | RATE_LIMITING | ✓ | ✓ | ✓ | - | - |
| **OBSERVABILITY** | STRUCTURED_LOGGING | ✓ | ✓ | ✓ | - | - |
| | OTEL_TRACING | ✓ | ✓ | ! | - | - |
| | PROMETHEUS_METRICS | ✓ | ✓ | ! | - | - |
| | REQUEST_ID_PROPAGATION | ✓ | ✓ | ✓ | - | - |
| **PRIVACY** | PII_REDACTION_IN_LOGS | ! | ! | - | - | - |
| | ACCOUNT_DELETION | ✓ | ✓ | ✓ | - | - |
| | DATA_EXPORT | - | - | - | - | - |
| | RETENTION_POLICY | ✓ | ✓ | ! | - | - |
| **DR** | BACKUP_SCRIPT | ✓ | ! | - | - | - |
| | RESTORE_PROCEDURE | ✓ | - | - | - | - |
| | RPO_DOCUMENTED | ✓ | - | - | - | - |
| | RTO_DOCUMENTED | ✓ | - | - | - | - |
| **DEPLOYMENT** | DOCKERFILES | ✓ | ✓ | ! | - | - |
| | TERRAFORM | ✓ | - | - | - | - |
| | CLOUD_BUILD | ✓ | - | - | - | - |
| | SECRET_MANAGER | ✓ | - | - | - | - |
| | STAGING_SEPARATION | ✓ | - | - | - | - |

---

## Notes on partial (`!`) capabilities

**SIGNUP / LOGIN / REFRESH**: These flows are handled entirely by Supabase Auth (client-side SDK). The backend has no `/auth/signup`, `/auth/login`, or `/auth/refresh` endpoints. If the capability requires a backend implementation, it is not present.

**HYBRID_RERANKING**: Vector search and FTS search are both implemented. Merging/reranking results from both into a unified ranked list is scaffolded but the reranking step is not complete.

**PROMPT_VERSIONING**: `rubric_version` is stored on `turn_scores`. Full prompt versioning with a registry of named prompt versions is not yet implemented.

**BARGE_IN**: The cancellation infrastructure (`cancellation.py`, `CancellationHelper`) exists. End-to-end barge-in (user speech cancelling TTS mid-stream) is partially wired.

**CODING (SANDBOXED_EXECUTION, RESOURCE_LIMITS)**: Code execution exists: `coding_engine.py` runs user-submitted Python in a subprocess with configurable time limit and Linux resource limits (`RLIMIT_AS`, `RLIMIT_NPROC`, `RLIMIT_NOFILE`). Marked `!` because the subprocess runs in the same container (not a separate network-isolated sandbox), and results are not validated against hidden test sets — only the caller-supplied test cases.

**CODING (HIDDEN_TESTS)**: Not implemented. Problem definitions include sample test cases; there are no server-side hidden test cases that the user cannot see before submission.

**NO_HIRE_PROBABILITY**: The readiness endpoint computes multi-dimensional scores. A specific no-hire probability output is not yet implemented.

**PII_REDACTION_IN_LOGS**: Structured logging is in place. Automatic PII scrubbing from log fields is not implemented.

**DATA_EXPORT**: Account deletion is implemented. A user-facing data export (GDPR Article 20) endpoint does not exist yet.

**BACKUP_SCRIPT INTEGRATED**: The script exists and runs correctly. Integration with a scheduled Cloud Run Job is not yet provisioned in Terraform.
