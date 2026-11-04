# PRAXIS InterviewOS — OWASP API Security Top 10 Verification

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Standard:** OWASP API Security Top 10 (2023 Edition)  

---

## 1. Compliance Mapping & Verification Evidence

| OWASP Vulnerability | Risk Description | PRAXIS Architectural Mitigation | Verified Test Suite | Status |
|---|---|---|---|:---:|
| **API1:2023 Broken Object Level Authorization (BOLA / IDOR)** | User accesses another candidate's session, resume, or profile. | PostgreSQL `FORCE ROW LEVEL SECURITY` on all 70 tables; context set to verified JWT `sub`. | `tests/security/test_rls_isolation.py`, `backend/tests/security/test_rls_isolation.py` | **PASS** |
| **API2:2023 Broken Authentication** | Forged tokens, algorithm `none`, expired tokens, weak keys. | Strict asymmetric/HMAC verification, `alg="none"` rejected, 32+ byte keys enforced. | `tests/security/test_jwt_rls_context.py`, `backend/tests/hardening/test_jwt_auth.py` | **PASS** |
| **API3:2023 Broken Object Property Level Authorization** | Mass assignment, exposure of internal attributes. | Explicit Pydantic response models (`from_attributes=True`), internal secrets excluded. | `backend/tests/api/test_openapi_contract.py` | **PASS** |
| **API4:2023 Unrestricted Resource Consumption** | DoS via infinite loops, token exhaustion, unbounded uploads. | Sliding window token bucket rate limiting; 15MB file cap; 4000 token session caps. | `backend/app/rate_limiter.py`, `backend/tests/hardening/test_authorization.py` | **PASS** |
| **API5:2023 Broken Function Level Authorization (BFLA)** | Non-admin executes administrative actions (e.g. `/admin/users/ban`). | `require_admin` dependency checks verified admin role in database before execution. | `backend/tests/security/test_admin_auth.py`, `tests/security/test_admin_auth.py` | **PASS** |
| **API6:2023 Unrestricted Access to Sensitive Business Flows** | Automated scraping of question bank or rapid answer generation. | Per-route rate limits on question generation and LLM debrief endpoints. | `backend/app/rate_limiter.py` | **PASS** |
| **API7:2023 Server Side Request Forgery (SSRF)** | Attacker forces backend to fetch internal metadata services (`169.254.169.254`). | `SSRFGuard` validates URLs against loopback, link-local, private RFC 1918 ranges. | `backend/tests/security/test_ssrf_defense.py` | **PASS** |
| **API8:2023 Security Misconfiguration** | Stack traces in errors, missing security headers, open CORS. | `CORSMiddleware` with explicit allowed origins; standard JSON errors without tracebacks. | `backend/app/middleware.py`, `backend/tests/api/test_routers_smoke.py` | **PASS** |
| **API9:2023 Improper Inventory Management** | Undocumented endpoints, rogue legacy APIs. | Auto-generated OpenAPI specification validated against registered FastAPI routes. | `backend/tests/api/test_openapi_contract.py` | **PASS** |
| **API10:2023 Unsafe Consumption of APIs** | Blind trust in third-party LLM output. | Pydantic schema validation on all structured LLM responses; fallback error propagation. | `packages/ai-gateway/praxis_ai_gateway/output_safety.py` | **PASS** |
