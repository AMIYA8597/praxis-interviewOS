# PRAXIS InterviewOS — Privacy & Sensitive Data Map

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: PRIVACY & GDPR COMPLIANCE REPORT  

---

## 1. Data Classification Matrix

| Data Asset | Sensitivity | Storage Location | Access Controls | Retention Policy | Third-Party Flow |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Account Identity** (Email, User ID) | Confidential | `auth.users`, `profiles` | RLS (`auth.uid() = id`), Encrypted DB volume | Account lifetime | Supabase Auth |
| **Resumes & CVs** (PDF/DOCX documents) | Highly Confidential | GCS bucket `resumes`, DB `documents` | Private bucket, 15-min signed URLs, RLS | Until deleted by user | Stripped before AI routing |
| **Interview Transcripts** (Spoken text) | Confidential | DB `session_turns` | RLS (`candidate_id = auth.uid()`) | Retained for debrief & study generation | Sent to AI Gateway for scoring |
| **Raw Spoken Audio** (PCM16 chunks) | Highly Confidential | Bounded memory buffer (volatile) | Ephemeral (<30s turn ring buffer) | Discarded immediately after ASR | Never persisted to permanent storage |
| **AI Evaluation Scores & Debriefs** | Confidential | DB `session_debriefs`, `evaluations` | RLS (`candidate_id = auth.uid()`) | Retained for readiness estimation | None (generated internally) |
| **Vector Embeddings** (RAG chunks) | Confidential | DB `document_chunks` (pgvector) | RLS, candidate ID query boundary | Lifetime of parent resume | Generated via embedding model |
| **Study Reviews & Cards** (SM-2 items) | Confidential | DB `study_items`, `study_reviews` | RLS (`candidate_id = auth.uid()`) | Spaced repetition schedule | None |

---

## 2. Privacy Principles Enforced
1. **Data Minimization**: Only information essential for technical interview preparation is collected.
2. **No Persistent Audio Storage**: Raw acoustic waveforms are processed strictly in volatile memory for real-time transcription and immediately discarded.
3. **Transparent Readiness Indicators**: Evaluation scores explicitly report whether they are `MEASURED`, `ESTIMATED`, `DEGRADED`, or `UNAVAILABLE`.
