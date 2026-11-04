# PRAXIS InterviewOS — Client Authentication & Identity Integration Guide

**Document Version:** 1.0.0  
**Target Audience:** Independent Frontend Engineers (Web, Mobile, Desktop, CLI)  

---

## 1. Authentication Architecture

PRAXIS InterviewOS delegates identity issuance to Supabase Auth (or compatible OAuth/OIDC identity providers) and cryptographically verifies JWT tokens on the backend using standard JSON Web Key Sets (JWKS).

```
[Client App]
     │
     │ 1. Sign In / Exchange Credentials
     ▼
[Supabase Auth / OIDC Provider]
     │
     │ 2. Return { access_token, refresh_token, expires_in }
     ▼
[Client App]
     │
     │ 3. HTTPS REST Request: Authorization: Bearer <access_token>
     ▼
[PRAXIS Core API]
     │
     │ 4. Verify Signature against JWKS (iss, aud, exp, sub)
     │ 5. Derive RLS context: SET LOCAL request.jwt.claims = ...
     ▼
[Authoritative PostgreSQL]
```

---

## 2. Making Authenticated Requests

All protected REST `/api/v1/*` endpoints require the JWT passed in the HTTP `Authorization` header:

```http
GET /api/v1/candidates/me HTTP/1.1
Host: api.praxis.domain
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### 2.1 Standard Authentication Error Responses
- **Missing Token (HTTP 401):**
  ```json
  {
    "detail": "Missing Authorization header"
  }
  ```
- **Expired Token (HTTP 401):**
  ```json
  {
    "detail": "Token expired"
  }
  ```
- **Forged or Invalid Token (HTTP 401):**
  ```json
  {
    "detail": "Invalid token signature"
  }
  ```

---

## 3. Realtime WebSocket Authentication

To authenticate the binary WebSocket connection (`/ws/sessions/{session_id}`):
Pass the access token as a URL query parameter:
```
wss://<REALTIME_HOST>/ws/sessions/<SESSION_ID>?token=<ACCESS_TOKEN>
```
The server validates the JWT and verifies that `sub` matches the candidate who owns the session. If unauthorized or expired, the WebSocket closes immediately with close code `4401 (Unauthorized)`.
