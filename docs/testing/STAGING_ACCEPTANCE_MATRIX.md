# PRAXIS InterviewOS — Staging Acceptance Matrix

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Acceptance Journey Matrix

| Journey ID | Workflow Name | Critical Capabilities Verified | Empirical Evidence | Final Verdict |
|---|---|---|---|:---:|
| **Journey A** | Candidate Onboarding | Candidate creation, profile settings, target roles | `tests/acceptance/test_independent_api_client.py` | **PASS** |
| **Journey B** | Resume Intelligence | Extraction, text chunking, 384-dim BGE embedding, DB storage | `scripts/run_synthetic_e2e_journey.py` Step 2 | **PASS** |
| **Journey C** | Job Intelligence | JD parsing, requirement graph, explainable match score | `scripts/run_synthetic_e2e_journey.py` Step 1 | **PASS** |
| **Journey D** | Technical Interview | 18-byte framing, Silero VAD, Whisper STT, turn debrief | `scripts/run_synthetic_e2e_journey.py` Steps 4-8 | **PASS** |
| **Journey E** | Behavioral Interview | STAR completeness scoring, ownership evaluation | `backend/tests/evaluation/test_behavioral_calibration.py` | **PASS** |
| **Journey F** | System Design Interview | 24-phase state machine, architecture trade-offs | `backend/tests/services/test_matching.py` | **PASS** |
| **Journey G** | Coding Interview | Non-root sandbox isolation, zero egress, 5s timeout | `backend/tests/services/test_coding_sandbox.py` | **PASS** |
| **Journey H** | Study & Learning Loop | Weakness identification, SM-2 interval scheduling | `backend/tests/services/test_sm2.py`, `tests/api/test_study.py` | **PASS** |
| **Journey I** | Resume Tailoring | Verified candidate claim grounding vs JD requirements | `realtime-agent/tests/unit/test_5tier_claim_grounding.py` | **PASS** |
| **Journey J** | Failure Recovery | Provider rate limit & server outage graceful handling | `packages/ai-gateway/tests/integration/test_gateway_failover.py` | **PASS** |
| **Journey K** | Data Lifecycle | GDPR archive export, irreversible cascading deletion | `tests/integration/test_deletion_cascade.py`, `backend/tests/workers/test_deletion_job.py` | **PASS** |
| **Journey L** | Cross-User Security | Dynamic multi-tenant RLS isolation on all 70 tables | `tests/security/test_rls_isolation.py` | **PASS** |
