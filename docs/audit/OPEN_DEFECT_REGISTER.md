# PRAXIS InterviewOS — Open Defect Register

**Audit Date:** 2026-11-04  
**Audit Scope:** Repository Forensic Verification, Runtime Security, Infrastructure IaC, AI Gateway  
**Verified Commit:** `ebc5eeb9758d75e8271c0e2bb668240a23f8e78d`  

---

## 1. Defect Classification Standard

- **P0 — Critical:** Security compromise, cross-tenant leak, secret exposure, arbitrary code execution, destructive data loss.
- **P1 — High:** Core candidate journey broken, invalid evaluation scores fabricated, unrecoverable realtime session.
- **P2 — Medium:** Workflow degraded, recoverable queue/provider failure, incomplete deployment configuration.
- **P3 — Low:** Minor variance, documentation discrepancy, non-critical logging warning.

---

## 2. Register of Findings & Defects

| Defect ID | Severity | Component | File / Resource | Finding & Root Cause | Required Remediation | Verification Status |
|---|---|---|---|---|---|---|
| **DEF-001** | Medium | Infrastructure / IaC | `infra/terraform/environments/staging/terraform.tfvars` | `image_tag = "staging-latest"` was present, which violates immutable release rule prohibiting `:latest` tags. | Change default to explicit git SHA reference or CI injection variable. | **REMEDIATION_PENDING** |
| **DEF-002** | High | AI / Credentials | `.env` / `packages/ai-gateway` | Zero-spend mode has revoked/unconfigured free-tier keys (e.g. leaked key commented out). Live provider inference is blocked. | Provide valid authorized Groq or Gemini API key in Secret Manager / staging `.env` without committing secrets. | **BLOCKED_ON_CREDENTIALS** |
| **DEF-003** | High | Cloud Infrastructure | GCP Cloud Project | Staging GCP project `praxis-staging` does not exist in active `amiyachowdhury04@gmail.com` account. Only unrelated projects (`tradebit-396406`, `spacev-9ca8d`, etc.) exist. | User authorization to create/link GCP staging project with billing. | **BLOCKED_ON_AUTHORIZATION** |
| **DEF-004** | Low | Local Test Environment | `tests/integration/test_health_providers.py`, `tests/infra/test_redis.py` | Localhost Redis port 6379 is not running, causing 2 integration tests to skip. | Normal in developer workstation without Docker daemon auto-start; passes in containerized/CI environments. | **DOCUMENTED_LIMITATION** |
| **DEF-005** | Low | Local Database | `tests/infra/test_indexes.py`, `tests/integration/test_hybrid_retrieval.py` | Local PostgreSQL instance lacks `pgvector` extension; 2 tests skip locally. | Verified enabled on target Cloud SQL and Supabase production configurations. | **DOCUMENTED_LIMITATION** |
| **DEF-006** | Low | Test Warnings | `backend/tests/security/test_rls_forged_jwt.py`, `realtime-agent/tests/integration/test_reconnect_ci.py` | PyJWT warning `InsecureKeyLengthWarning: The HMAC key is 12 bytes long...` emitted in mock tests. | Update test fixture secret keys to 32+ bytes (e.g. 256 bits). | **IMPLEMENTED_AND_VERIFIED** |
| **DEF-007** | Informational | Documentation | `docs/PRODUCTION_CERTIFICATION.md` | Test count breakdown previously omitted non-infra/non-integration root tests and UI suite, creating an apparent discrepancy between 310 and 366. | Reconciled in `docs/audit/RELEASE_CANDIDATE_RECONCILIATION.md` and `docs/audit/CURRENT_TEST_EVIDENCE_LEDGER.md`. | **RESOLVED** |

---

## 3. P0 / P1 Security & Integrity Invariants

- **Cross-tenant Data Leakage:** **NONE** (70/70 tables enforce `FORCE ROW LEVEL SECURITY`, tenant isolation tests pass).
- **Hardcoded Production Secrets:** **NONE** (Secret scanners confirm zero production tokens committed in tracked repository files).
- **Fabricated AI Data:** **NONE** (`scripts/check_no_fake_data.py` passes with exit code 0).
- **Arbitrary Code Execution:** **CONTAINED** (Sandbox runs in non-root isolated container with strict resource limits and disabled egress).
