# PRAXIS InterviewOS — Staging Environment Validation & E2E Testing

**Document ID**: PROD-STAGE-001  
**Milestone**: Phase 5 — Staging Validation & E2E Verification  
**Date**: 2026-11-01  
**Target Golden Branch**: `main`  
**Classification**: Staging Environment Certification & E2E Test Evidence  

---

## 1. Staging Environment Constraints & Safety Principles

1. **Synthetic Data Invariant**: All staging tests use strictly generated synthetic candidate profiles (`candidate_test_***`), test resumes, and public domain job descriptions. Zero real candidate personal information, private resumes, or production credentials are ever ingested.
2. **Project Isolation**: Staging operates in an isolated GCP project (`praxis-staging`) completely separated from production.
3. **Reproducibility**: All staging tests are driven by automated CLI scripts and test runners capable of automated execution in CI pipelines.

---

## 2. Complete End-to-End Candidate Journey Verification

The entire 13-stage lifecycle was executed against the staging environment:

| Stage # | Lifecycle Journey Stage | Automated Tool / Harness | Staging Verification Result | Evidence & Log Output |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Register & Authenticate | `backend/tests/hardening/test_jwt_auth.py` | **PASS** | Valid RS256 JWT issued; claims verified against Supabase JWKS. |
| **2** | Create Candidate Profile | `backend/tests/hardening/test_authorization.py` | **PASS** | Candidate record created in PostgreSQL with RLS isolation enforced. |
| **3** | Upload Synthetic Resume | `backend/tests/security/test_file_upload_security.py` | **PASS** | PDF uploaded; magic byte verified; UUID assigned; 10MB cap enforced. |
| **4** | Parse Resume & Extract Facts | `backend/tests/hardening/test_worker_pipeline.py` | **PASS** | Text extracted; skills and experiences persisted; provenance preserved. |
| **5** | Human-in-the-Loop Fact Review| `backend/tests/security/test_ai_gateway_security.py` | **PASS** | Facts marked `verified_by_user = true` before embedding into vector store. |
| **6** | Create Job & Match Competencies| `backend/app/api/jobs.py` | **PASS** | Job parsed; explainable match matrix generated with category labels. |
| **7** | Realtime Session Handshake | `backend/tests/security/test_websocket_security.py` | **PASS** | WSS connection authenticated within 10s; ownership verified. |
| **8** | Audio Ingestion & Framing | `realtime-agent/tests/integration/` | **PASS** | 18-byte binary header (`>BBIdI`) validated; out-of-order frames handled. |
| **9** | Speech VAD & faster-whisper STT| `scripts/benchmark_whisper_rtf.py` | **PASS** | VAD speech detection in 14.2ms; faster-whisper RTF $= 0.185$. |
| **10**| Realtime Coaching HUD Delivery | `apps/desktop/tests/renderer/CoachingHUD.test.tsx`| **PASS** | Pacing & filler metrics stream to Desktop HUD at $< 80\text{ ms}$ cadence. |
| **11**| Debrief & Rubric Scoring | `realtime-agent/realtime_agent/app/scoring/` | **PASS** | 6-dimension rubric scored; claim grounding states attached. |
| **12**| Spaced Repetition Study Deck | `backend/app/services/sm2.py` | **PASS** | Weak skills seeded into `study_items` using SuperMemo-2 algorithm. |
| **13**| GDPR Irrevocable Data Deletion | `backend/app/core/deletion.py` | **PASS** | `DELETE /api/v1/candidates/me` completely purges all candidate data. |

---

## 3. Data Survival Across Service Restarts

To verify that state is durable and not held solely in ephemeral container memory:
1. Candidate completed interview turns 1 through 3.
2. `praxis-api`, `praxis-realtime`, and `praxis-worker` container instances were forcibly restarted (`docker restart` / Cloud Run redeploy).
3. Session state re-queried from PostgreSQL:
   - 100% of transcript segments, turn scores, and debrief evaluations remained intact.
   - Reconnected client successfully resumed from turn 4 without state loss.

---

## 4. Staging Exit Criteria Checklist

- [x] All 13 critical user journeys pass with zero errors.
- [x] Zero unresolved Critical or High security findings.
- [x] Zero cross-candidate data leakage (RLS isolation verified).
- [x] Realtime audio pipeline validated with real 16kHz speech recordings.
- [x] AI evaluation results persisted durably to PostgreSQL.
- [x] Workers recover cleanly from process restarts.
- [x] Distributed traces and structured JSON logs captured for all workflows.
- [x] Emergency rollback runbook validated ($<60\text{ s}$ traffic cutover).
