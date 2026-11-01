# PRAXIS InterviewOS — Trust Boundaries Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: ARCHITECTURAL SECURITY SPECIFICATION  

---

## 1. Trust Boundary Map

```
[ UNTRUSTED ZONE: Public Internet / End Users ]
       |
       | HTTPS (TLS 1.3)
       v
+=======================================================================+
| TRUST BOUNDARY 1: Web Browser & Next.js Client                        |
| - Treats all user inputs, resumes, and third-party scripts as hostile |
| - Validates origin, sanitizes DOM output, uses HttpOnly cookies       |
+=======================================================================+
       |
       | HTTPS / WSS (Bearer RS256 JWT)
       v
+=======================================================================+
| TRUST BOUNDARY 2: API Gateway & Reverse Proxy / FastAPI               |
| - Verifies JWT cryptographically against Supabase JWKS                |
| - Enforces per-IP and per-account rate limits                         |
| - Validates Pydantic schemas, strips unexpected fields                |
+=======================================================================+
       |
       +-------------------------------+--------------------------------+
       |                               |                                |
       | Internal PostgreSQL Protocol  | Binary Framing (>BBIdI)        | Private HTTP
       v                               v                                v
+=============================+ +==============================+ +==============================+
| TRUST BOUNDARY 3:           | | TRUST BOUNDARY 4:            | | TRUST BOUNDARY 5:            |
| PostgreSQL & RLS Engine     | | Realtime Speech Agent        | | AI Gateway & External LLMs   |
| - 71 tables with RLS        | | - 18-byte big-endian header  | | - Strips private secrets     |
| - Enforces candidate scope  | | - Bounded audio buffers      | | - XML tags for untrusted data|
| - Fails closed on untrusted | | - Validates session ownership| | - SSRF blocked on base URLs  |
+=============================+ +==============================+ +==============================+
                                       |
                                       | Isolated Execution Channel
                                       v
                                +==============================+
                                | TRUST BOUNDARY 6:            |
                                | Coding Sandbox Execution     |
                                | - Ephemeral non-root container|
                                | - Zero network access        |
                                | - CPU/Memory resource bounds |
                                +==============================+
```

---

## 2. Detailed Boundary Invariant Descriptions

### Boundary 1: Browser to Web Application
- **Direction**: Inbound from end user.
- **Enforcement**: Content Security Policy, X-Content-Type-Options: nosniff, Strict-Transport-Security, and HttpOnly SameSite=Lax cookies.
- **Rule**: Client never receives raw service role keys or master database credentials.

### Boundary 2: Client to Backend API
- **Direction**: Inbound HTTP REST requests.
- **Enforcement**: `backend/app/auth.py` validates RS256 signatures, `exp`, `iss`, and `aud`.
- **Rule**: Client-supplied `candidate_id` or `user_id` query parameters are never trusted for authorization; `current_user.id` is derived strictly from the cryptographically verified JWT principal.

### Boundary 3: Application to PostgreSQL
- **Direction**: Internal database queries.
- **Enforcement**: Supabase Row Level Security (RLS) policies evaluate `auth.uid() = candidate_id` on every `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.
- **Rule**: Even if an application bug omitted a `WHERE` clause, the database engine drops non-owned rows.

### Boundary 4: Client to Realtime Agent
- **Direction**: Inbound WebSocket binary frames on port 8001.
- **Enforcement**: First 18 bytes must adhere to `proto_ver=1`, `frame_type=1`, monotonic `client_seq`, valid `capture_ts`, and `payload_len <= 65536`.
- **Rule**: Audio buffer allocates a maximum 30-second ring buffer per candidate turn to prevent memory exhaustion attacks.

### Boundary 5: Backend to External AI Providers
- **Direction**: Outbound requests to OpenAI, OpenRouter, DeepSeek, Google Gemini.
- **Enforcement**: Custom base URLs undergo strict SSRF validation (blocking loopback `127.0.0.1`, RFC1918 private ranges, and cloud metadata `169.254.169.254`). Candidate prompt inputs are isolated within `<untrusted_content>` tags.
- **Rule**: AI provider responses are treated as untrusted text and validated against JSON schemas before persisting into state.

### Boundary 6: Application to Code Execution Sandbox
- **Direction**: Candidate submitted Python/JavaScript code execution.
- **Enforcement**: Dedicated runner container running as unprivileged user `nobody`, read-only root filesystem, `--network none`, strict timeout (5 seconds), and RAM ceiling (128MB).
- **Rule**: Sandbox process has no access to host filesystem, Docker daemon socket, or database network.
