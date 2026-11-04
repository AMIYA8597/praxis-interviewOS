# PRAXIS InterviewOS — Candidate File Upload & Document Processing Guide

**Document Version:** 1.0.0  
**Target Audience:** Independent Frontend Engineers  

---

## 1. Document Upload Workflow

Uploading candidate resumes and job descriptions is a 3-step asynchronous workflow:

```
[Client]                      [PRAXIS API]                     [Object Storage / GCS]
   │                               │                                     │
   │ 1. POST /api/v1/resumes       │                                     │
   │    (multipart/form-data)      │                                     │
   ├──────────────────────────────►│                                     │
   │                               │ 2. Validate MIME & upload blob      │
   │                               ├────────────────────────────────────►│
   │                               │ 3. Enqueue process_resume ARQ task │
   │ 4. HTTP 202 Accepted          │                                     │
   │    {"id": "<doc_id>",         │                                     │
   │     "status": "processing"}   │                                     │
   │◄──────────────────────────────┤                                     │
   │                               │                                     │
   │ 5. GET /api/v1/resumes/<id>   │                                     │
   ├──────────────────────────────►│                                     │
   │ 6. HTTP 200 OK                │                                     │
   │    {"status": "ready",        │                                     │
   │     "chunks_count": 5}        │                                     │
   │◄──────────────────────────────┤                                     │
```

---

## 2. API Contract Specifications

### 2.1 Upload Resume
- **Endpoint:** `POST /api/v1/resumes`
- **Headers:** `Authorization: Bearer <JWT>`, `Content-Type: multipart/form-data`
- **Accepted File Formats:**
  - PDF (`application/pdf`)
  - Microsoft Word (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
  - Plain Text (`text/plain`)
- **Size Limit:** Max 15 MB (HTTP 413 Payload Too Large if exceeded).

### 2.2 Polling Processing Status
- **Endpoint:** `GET /api/v1/resumes/{document_id}`
- **Response Schema:**
  ```json
  {
    "id": "fdcd5ef2-ff6a-4099-a604-5212ce276276",
    "filename": "Alex_Morgan_Resume.pdf",
    "status": "ready",
    "chunks_count": 4,
    "created_at": "2026-11-04T12:00:00Z"
  }
  ```
  Status transitions: `pending` -> `processing` -> `ready` (or `failed`).

### 2.3 Retrieving Extracted Facts & Verified Claims
- **Endpoint:** `GET /api/v1/resumes/{document_id}/facts`
- Returns structured skills, experiences, and verifiable metric claims extracted from the resume with chunk provenance offsets.
