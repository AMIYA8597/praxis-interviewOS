# PRAXIS InterviewOS — API Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: API DEFENSE & VALIDATION REPORT  

---

## 1. Input Validation & Strict Serialization

All REST endpoints in PRAXIS are built with FastAPI and Pydantic v2 schemas:
1. **Pydantic Type Validation**: Strict validation of string lengths, integer bounds, enums, and UUID formats.
2. **Rejection of Unknown / Unexpected Fields**: Payloads undergo validation against explicit schemas (`SessionCreate`, `CandidateUpdate`, etc.).
3. **Structured Responses**: Endpoints declare explicit `response_model` types preventing accidental serialization of sensitive internal database columns (e.g. password hashes, internal tokens, or raw connection strings).

---

## 2. Injection Defenses

### 2.1 SQL Injection Protection
- All database queries use SQLAlchemy 2.0 with parameterized `select()`, `insert()`, `update()`, and `delete()` constructs or explicitly bound `text()` queries (e.g. `text("SELECT * FROM candidates WHERE id = :id"), {"id": candidate_id}`).
- String concatenation into SQL queries is strictly prohibited and verified by `ruff` and `bandit` static analysis.

### 2.2 Shell Command Injection Protection
- User-supplied inputs are never passed to `os.system()` or `subprocess.Popen(..., shell=True)`.
- System utilities (e.g. audio processing, sandbox runners) execute via argument lists (`["ffmpeg", "-i", ...], shell=False`).

---

## 3. Rate Limiting & Denial-of-Service Defenses

- **Redis Token Bucket**: Endpoints enforce distributed rate limiting via Redis (`backend/app/rate_limiter.py`).
- **Endpoint Limits**:
  - Auth Token Verification: 120 requests / minute per IP.
  - Document Uploads: 10 uploads / hour per candidate.
  - Practice Session Creation: 20 sessions / hour per candidate.
  - AI Gateway Turn Scoring: 60 turns / minute per session.
- **Payload Size Ceilings**:
  - Multipart resume upload: Max 10 MB.
  - JSON request body: Max 1 MB.

---

## 4. Error Handling & Information Disclosure Prevention

1. **Standard Error Envelope**: All API exceptions format into structured JSON responses:
   ```json
   {
     "code": "not_found",
     "message": "Resource not found or unauthorized",
     "request_id": "a1b2c3d4-..."
   }
   ```
2. **Production Stack Trace Suppression**: Unhandled server exceptions (500) log the stack trace internally with correlation `request_id`, returning a generic "Internal server error" to the client.
3. **No Database Connection Strings or Secrets**: Sensitive connection URLs and API keys are scrubbed before logging.
