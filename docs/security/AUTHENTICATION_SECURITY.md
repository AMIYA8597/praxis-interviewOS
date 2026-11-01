# PRAXIS InterviewOS — Authentication & Identity Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: AUTHENTICATION AUDIT & VERIFICATION REPORT  

---

## 1. Authentication Architecture & Verification

PRAXIS utilizes Supabase Auth issuing RS256 asymmetric JSON Web Tokens (JWT). The backend (`backend/app/auth.py`) implements a zero-trust cryptographic verification gate before any request reaches application route handlers.

```
+---------------+     1. Authorization: Bearer <TOKEN>     +-------------------+
| Client / API  | ---------------------------------------> | FastAPI Middleware|
+---------------+                                          +-------------------+
                                                                     |
                                                           verify_jwt(token)
                                                                     |
                                                                     v
                                                   +-----------------------------------+
                                                   | 1. Structural Syntax Check (x.y.z)|
                                                   | 2. Header Extraction (alg, kid)   |
                                                   | 3. Algorithm Restriction (RS256)  |
                                                   | 4. JWKS Discovery & Caching       |
                                                   | 5. RS256 Asymmetric Verification  |
                                                   | 6. Claims: sub, exp, iat, iss, aud|
                                                   +-----------------------------------+
```

---

## 2. Cryptographic & Operational Invariants

### 2.1 Algorithm Restriction & Confusion Defenses
- **Asymmetric Allowlist**: Only `RS256`, `RS384`, `RS512`, `ES256`, `ES384`, `PS256`, and `EdDSA` are permitted.
- **Symmetric Isolation**: Legacy `HS256` tokens require explicit `SUPABASE_JWT_SECRET` configuration and are validated against HMAC secrets, completely preventing algorithm substitution / "None" attack vectors.
- **"none" Algorithm Rejection**: Tokens specifying `alg: "none"` or unapproved algorithms fail with `AuthError(reason="unsupported_alg")`.

### 2.2 Key Rotation & Resilient Caching
- **Cluster Caching**: Validated public keys from Supabase's `/.well-known/jwks.json` are cached in Redis (`cache:jwks`) for 3600 seconds (`JWKS_CACHE_TTL_S`).
- **In-Process Fallback**: In-memory cache (`_memory_jwks`) ensures auth verification remains operational during transient Redis disruptions.
- **Key Rotation**: When a token carries an unrecognized `kid`, the system performs a single rate-limited cache bypass (`JWKS_REFRESH_COOLDOWN_S = 10s`) to fetch updated keys from Supabase.
- **Fail-Closed Semantics**: If the JWKS endpoint is unreachable and the key is unknown, the request fails with `AuthProviderUnavailable` (HTTP 503) without exposing token contents.

### 2.3 Claims Validation
- `exp` (Expiration): Mandatory. Tokens past expiration fail immediately with `AuthError(reason="expired")`.
- `sub` (Subject): Mandatory UUID. Used strictly as the verified principal.
- `aud` (Audience): Checked against `settings.JWT_AUDIENCE` (`authenticated`).
- `iss` (Issuer): Checked against `settings.jwt_issuer` (`{SUPABASE_URL}/auth/v1`).

---

## 3. Automated Test Evidence & Verification Matrix

Automated verification tests are maintained in `backend/tests/hardening/test_jwt_auth.py` and `backend/tests/security/test_authentication_security.py`:

| Test ID | Test Scenario | Expected Behavior | Verification Status |
| :--- | :--- | :--- | :--- |
| `AUTH-01` | Valid RS256 token signed by JWKS key | Decoded principal returned (HTTP 200) | **PASS** |
| `AUTH-02` | Expired RS256 token | Rejected with HTTP 401 `Session expired` | **PASS** |
| `AUTH-03` | Token signed by untrusted/forged private key | Rejected with HTTP 401 `Invalid or expired session` | **PASS** |
| `AUTH-04` | Wrong audience (`aud: "wrong"`) | Rejected with HTTP 401 `Invalid or expired session` | **PASS** |
| `AUTH-05` | Wrong issuer (`iss: "https://evil.com"`) | Rejected with HTTP 401 `Invalid or expired session` | **PASS** |
| `AUTH-06` | Algorithm set to `"none"` | Rejected with HTTP 401 `unsupported_alg` | **PASS** |
| `AUTH-07` | Symmetric HS256 signed with incorrect secret | Rejected with HTTP 401 | **PASS** |
| `AUTH-08` | Missing `sub` claim in payload | Rejected with HTTP 401 `missing_sub` | **PASS** |
| `AUTH-09` | Key rotation with new `kid` | Successfully re-fetches JWKS and verifies | **PASS** |
| `AUTH-10` | JWKS endpoint completely unreachable | Fails closed with HTTP 503 | **PASS** |
| `AUTH-11` | Client supplies fake `X-User-Id` header | Header ignored; identity taken strictly from token | **PASS** |
| `AUTH-12` | Production environment with `AUTH_DEV_BYPASS` | Dev bypass strictly disabled in production | **PASS** |
