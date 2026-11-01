# PRAXIS InterviewOS — File Upload & Document Processing Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: DOCUMENT SECURITY AUDIT & SPECIFICATION  

---

## 1. Document Processing Threat Analysis

PRAXIS accepts candidate resumes in PDF, DOCX, and TXT formats for parsing, skill extraction, and vector embedding. Uploaded documents represent untrusted external input and can serve as vectors for:
- Path traversal (e.g., `../../etc/passwd` filenames).
- Decompression bombs (e.g., zip-bombs inside DOCX packages).
- Parser memory exhaustion (e.g., complex nested PDF streams).
- Embedded prompt injection attacks intended to hijack LLM evaluators.

---

## 2. Ingestion Defense Pipeline (`backend/app/core/uploads.py`)

```
[ Uploaded File Stream ]
         |
         v
[ 1. Streamed Chunk Reader (read_limited) ]
  - Reads in 64KB chunks.
  - Aborts with HTTP 413 (PayloadTooLargeError) if bytes > 10MB.
         |
         v
[ 2. Filename Sanitization (sanitize_filename) ]
  - Strips all path separators (\ and /).
  - Normalizes Unicode via NFKD to ASCII.
  - Caps stem at 100 characters; strips non-alphanumeric chars.
         |
         v
[ 3. Magic-Byte Sniffing (sniff_mime) ]
  - PDF: Verifies %PDF- header.
  - DOCX: Verifies PK\x03\x04 zip header AND inspects package contents
    requiring word/document.xml and [Content_Types].xml.
  - TXT: Rejects binary control characters (null bytes).
         |
         v
[ 4. Isolated Storage Keying (storage_key) ]
  - Stored under candidate_id/resumes/{document_id}/{safe_filename}.
  - Object storage enforce private-by-default permissions.
         |
         v
[ 5. Asynchronous Background Parsing (ARQ Worker) ]
  - Parsing runs in background worker, never blocking API threads.
  - Memory and execution timeouts (60 seconds) strictly enforced.
```

---

## 3. Verified Security Controls Matrix

| Test Scenario | Attack Input | Expected Result | Verification |
| :--- | :--- | :--- | :--- |
| File size > 10MB | 11MB file upload | HTTP 413 Payload Too Large | **PASS** (`test_uploads_sessions_study.py`) |
| Path traversal filename | `../../../etc/cron.d/evil.pdf` | Sanitized to `evil.pdf` under `candidate_id/` | **PASS** (`test_uploads_sessions_study.py`) |
| Spoofed extension | Executable named `resume.pdf` | Sniffing fails `%PDF-` check -> HTTP 415 | **PASS** (`test_uploads_sessions_study.py`) |
| Polyglot file | HTML file with `.pdf` extension | Magic byte sniffing rejects non-PDF | **PASS** (`test_uploads_sessions_study.py`) |
| Malformed zip structure | Corrupted DOCX zip header | `zipfile.BadZipFile` handled -> HTTP 400 | **PASS** (`test_uploads_sessions_study.py`) |
| Cross-tenant download | Candidate B requesting Alice's resume | HTTP 404 (Not Found) | **PASS** (`test_authorization.py`) |
