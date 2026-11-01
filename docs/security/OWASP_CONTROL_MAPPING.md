# PRAXIS InterviewOS — OWASP Control Mapping & Compliance Matrix

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: COMPLIANCE & CONTROL MAPPING  

---

## 1. OWASP Top 10 Web Application Security (2021)

| OWASP Category | PRAXIS Threat | Implemented Defense | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | Candidate B accessing Alice's interview session or resume | Multi-layer authorization: FastAPI dependency checks + PostgreSQL Row Level Security (RLS) on all 71 tables | `backend/tests/hardening/test_authorization.py` | **PASS** |
| **A02: Cryptographic Failures** | Sensitive secrets in transit or unencrypted database volumes | TLS 1.3 encryption in transit; AES-256 at rest; RS256 asymmetric JWT verification | `backend/tests/hardening/test_jwt_auth.py` | **PASS** |
| **A03: Injection** | SQL injection in search queries; command injection | Parameterized SQLAlchemy 2.0 queries; no shell execution with user input | `backend/tests/security/test_api_input_validation.py` | **PASS** |
| **A04: Insecure Design** | Cheating overlays; proctor bypass | Strict adherence to ADR-001 (Zero Proctor Evasion); no stealth overlays | Architectural review & test suite | **PASS** |
| **A05: Security Misconfiguration**| Insecure default headers; CORS wildcards | Enterprise headers (CSP, HSTS, X-Frame-Options: DENY, nosniff) via middleware; explicit CORS origin allowlist | `backend/app/middleware.py`, `apps/web/src/middleware.ts` | **PASS** |
| **A06: Vulnerable & Outdated Components**| Known CVE in python or npm dependencies | Automated dependency auditing (`pnpm audit`, `pip-audit`, Trivy); lockfile pinning | Dependency scan gate | **PASS** |
| **A07: Identification & Auth Failures** | JWT signature bypass; algorithm confusion | RS256 algorithm restriction; JWKS public key discovery & caching; no "none" algorithm | `backend/tests/hardening/test_jwt_auth.py` | **PASS** |
| **A08: Software & Data Integrity Failures**| Malicious PDF/DOCX exploit | Streamed size caps (10MB); filename sanitization; magic-byte validation | `backend/tests/hardening/test_uploads_sessions_study.py`| **PASS** |
| **A09: Security Logging & Monitoring Failures**| Missing audit logs; credentials printed in logs | Structured JSON logging; correlation request IDs; PII & secret scrubbing | `backend/tests/api/test_observability.py` | **PASS** |
| **A10: Server-Side Request Forgery (SSRF)**| Malicious AI provider URL targeting cloud metadata | Pre-connection IP check (`is_safe_url()`) blocking private IPs and `169.254.169.254` | `backend/tests/security/test_ssrf_defense.py` | **PASS** |

---

## 2. OWASP API Security Top 10 (2023)

| OWASP API Category | Description | PRAXIS Control Implementation | Status |
| :--- | :--- | :--- | :--- |
| **API1: Broken Object Level Auth (BOLA)** | IDOR on `/sessions/{id}` | Endpoint derives tenant strictly from verified token; returns 404 for foreign IDs | **PASS** |
| **API2: Broken Authentication** | Compromised / expired token | RS256 signature verification, `exp` claim validation, JWKS rotation | **PASS** |
| **API3: Broken Object Property Level Auth** | Mass assignment on candidate profile | Pydantic `CandidateUpdate` whitelist rejects unexpected fields | **PASS** |
| **API4: Unrestricted Resource Consumption** | Flooding AI evaluation endpoints | Redis token bucket rate limiting + monthly token budget guards | **PASS** |
| **API5: Broken Function Level Auth** | Regular candidate calling admin APIs | Admin endpoints require `is_admin` claim in token metadata | **PASS** |
| **API6: Server-Side Request Forgery** | Attacking internal Redis from API | `is_safe_url()` blocks loopback and private subnets | **PASS** |
| **API7: Security Misconfiguration** | Stack traces in API errors | Generic error responses with correlation IDs; debug off in production | **PASS** |
| **API8: Lack of Protection from Automated Threats** | Bot account creation | Rate limits on `/auth` and session creation | **PASS** |
| **API9: Improper Assets Management** | Unversioned or deprecated endpoints | Strict API versioning prefix `/api/v1/` on all routers | **PASS** |
| **API10: Unsafe Consumption of APIs** | Malformed response from OpenAI | Strict Pydantic JSON schema validation of all model responses | **PASS** |

---

## 3. OWASP Top 10 for Large Language Models (LLM)

| LLM Vulnerability | PRAXIS Implementation & Defense | Status |
| :--- | :--- | :--- |
| **LLM01: Prompt Injection** | `PromptBuilder` neutralizes closing delimiter tags and strips `<TRUSTED_CONTEXT>` | **PASS** |
| **LLM02: Insecure Output Handling** | Structured output parsing with regex secret scanning before persistence | **PASS** |
| **LLM03: Training Data Poisoning** | Third-party foundational models used with zero-retention / no-training flags | **PASS** |
| **LLM04: Model Denial of Service** | Token budget guards (`budget.py`) and turn audio limits (<30s) | **PASS** |
| **LLM05: Supply Chain Vulnerabilities** | LiteLLM and model dependencies pinned in `requirements-lock.txt` | **PASS** |
| **LLM06: Sensitive Information Disclosure**| System prompts enforce PII redaction; secret scanner intercepts keys in output | **PASS** |
| **LLM07: Insecure Plugin Design** | Tool calling allowlist; zero shell invocation from AI agents | **PASS** |
| **LLM08: Excessive Agency** | AI Gateway performs evaluation and question synthesis only; cannot modify DB | **PASS** |
| **LLM09: Overreliance** | 5-tier claim grounding provides factual source citations for all debrief claims | **PASS** |
| **LLM10: Model Theft** | Enterprise provider endpoints accessed via private server-side credentials | **PASS** |
