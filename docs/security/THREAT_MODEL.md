# PRAXIS InterviewOS — Enterprise Threat Model (STRIDE Methodology)

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: THREAT MODEL & RISK REGISTER  

---

## 1. Threat Actors & Asset Taxonomy

### 1.1 Threat Actor Profiles
1. **Anonymous Internet Attacker (EXT-01)**: Unauthenticated actor attempting to access public endpoints, probe for open ports, or exploit unauthenticated routes.
2. **Malicious Authenticated Candidate (EXT-02)**: Authenticated user attempting horizontal privilege escalation (accessing another candidate's interview debrief or resume) or vertical escalation (accessing administrative panels).
3. **Malicious Document Uploader (EXT-03)**: Actor uploading specially crafted PDF/DOCX files containing exploits, decompression bombs, or prompt injections.
4. **Compromised Dependency / Supply Chain (SUP-01)**: Malicious code introduced via npm or PyPI dependency updates.
5. **Malicious AI Provider / Rogue Base URL (PRV-01)**: Man-in-the-middle or malicious provider base URL configured to capture candidate queries or return poisoned payloads.
6. **Privileged Insider / Leaked Credential (INS-01)**: Actor possessing a compromised API key, service role key, or database connection string.

### 1.2 Critical Assets
- **A-01: Authentication Secrets & Tokens** (Supabase RS256 JWTs, service role keys, session cookies).
- **A-02: Candidate PII & Career Records** (Resumes, transcripts, audio recordings, job applications).
- **A-03: AI Evaluator Integrity** (Rubric scores, STAR completeness analysis, PRAXIS Readiness Estimates).
- **A-04: AI Provider Credentials** (OpenAI, OpenRouter, DeepSeek, Google Gemini API keys).
- **A-05: Infrastructure & Database** (PostgreSQL 71 relational tables, Redis worker queues, Cloud Run instances).

---

## 2. STRIDE Threat Matrix & Remediations

| Threat ID | STRIDE Category | Target Asset | Attack Scenario | Impact | Mitigation / Control | Residual Risk | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TH-01** | Spoofing | Auth Tokens (A-01) | Attacker signs a JWT with a forged key or arbitrary HMAC key | Complete account takeover | RS256 signature verification against Supabase JWKS; algorithm restriction to RS256 | Low (fails closed if JWKS unreachable) | **Critical** |
| **TH-02** | Tampering | Binary Audio (A-02) | Client modifies binary audio header bytes or sends malformed frame type | Realtime agent crash or buffer overflow | Strict 18-byte header parsing (`>BBIdI`), protocol version enforcement, payload length boundary checks | Low (malformed frames dropped) | **High** |
| **TH-03** | Repudiation | Audit Trail (A-05) | User denies requesting session deletion or admin changes | Inability to audit compliance or security incidents | PostgreSQL audit log table (`audit_logs`) tracking actor ID, action, timestamp, and IP | Low | **Medium** |
| **TH-04** | Information Disclosure | Candidate Data (A-02) | Candidate A accesses Candidate B's resume or debrief via IDOR | Cross-tenant privacy breach (GDPR violation) | PostgreSQL Row Level Security (RLS) on all tables; auth principal used as query tenant key | Very Low (enforced at DB engine layer) | **Critical** |
| **TH-05** | Information Disclosure | Vector RAG (A-02) | Candidate A's prompt retrieves document chunks belonging to Candidate B | Cross-candidate resume leakage | RAG queries filter strictly by `candidate_id = auth.uid()`; RRF merging enforces candidate boundary | Very Low | **Critical** |
| **TH-06** | Denial of Service | Realtime Agent (A-05) | Client floods WebSocket with oversized audio frames or high frequency | Memory exhaustion / CPU starvation on worker | Per-connection frame rate limiter, max payload size (64KB), bounded audio buffer | Low | **High** |
| **TH-07** | Elevation of Privilege | Electron Main (A-05) | XSS in renderer invokes privileged Node.js APIs via Electron IPC | Remote code execution on candidate desktop | `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, strict IPC allowlist | Very Low | **Critical** |
| **TH-08** | Tampering | AI Reasoning (A-03) | Prompt injection embedded in resume text overrides evaluator rubric | Falsified interview scores or bypassed evaluation | XML delimiter encapsulation (`<untrusted_content>`), system prompt prioritization | Low | **High** |
| **TH-09** | Information Disclosure | Secrets (A-04) | Provider error stack trace reveals OpenAI or Gemini API key in logs | API key compromise / financial abuse | Error redaction middleware, server-side credential isolation, Sentry redaction | Very Low | **High** |
| **TH-10** | Elevation of Privilege | Code Execution (A-05) | Candidate submits malicious Python script attempting sandbox escape | Backend server compromise / DB credential access | Ephemeral non-root container, network isolation, CPU/RAM quotas, read-only root FS | Low | **Critical** |

---

## 3. CVSS 4.0 Risk Assessments for Critical Threats

### TH-01: JWT Signature Bypass / Algorithm Confusion
- **CVSS 4.0 Vector**: `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H`
- **Score**: **9.3 (Critical)**
- **Remediation**: `backend/app/auth.py` strictly restricts `algorithms=["RS256"]`, validates `exp`, and caches Supabase public keys via JWKS with fail-closed semantics.

### TH-04: Cross-Tenant Data Access (IDOR via REST)
- **CVSS 4.0 Vector**: `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N`
- **Score**: **8.7 (High)**
- **Remediation**: Multi-layered authorization: FastAPI dependency checks session ownership, and Supabase RLS enforces `auth.uid() = candidate_id` at the PostgreSQL engine level.

### TH-07: Electron Renderer Privilege Escalation
- **CVSS 4.0 Vector**: `CVSS:4.0/AV:L/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H`
- **Score**: **8.5 (High)**
- **Remediation**: Main window explicitly disables Node.js integration, enables context isolation and sandboxing, and exposes only 12 narrow IPC functions through `contextBridge`.
