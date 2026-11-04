# PRAXIS InterviewOS — Secret Rotation & Credential Register

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Secret Hygiene & Policy

In compliance with Rule 0.2:
- *"Never log API keys, JWTs, passwords, resumes, private transcripts or sensitive candidate information."*
- *"Do not expose credentials through Git, CI output, logs, API responses or generated reports."*

All production credentials reside in Google Secret Manager or secure environment vaults. No plain-text production secrets exist in tracked Git history.

---

## 2. Secret Inventory & Rotation Procedures

| Secret Name | Purpose | Rotation Frequency | Zero-Downtime Strategy | Emergency Revocation Action |
|---|---|---|---|---|
| `praxis-jwt-secret` | Signs and verifies user session JWTs | 90 days | Multi-key verification window (accept key N and N-1; sign with N). | Revoke compromised key in Secret Manager; force user re-authentication. |
| `praxis-database-url` | PostgreSQL connection string | 180 days | Update password on database host; create new secret version in Secret Manager; deploy Cloud Run revision. | Change DB user password immediately; revoke old credentials. |
| `praxis-redis-url` | Memorystore / Redis connection string | 180 days | Dual-auth Redis token transition where supported; update secret version. | Rotate Redis AUTH token via GCP console/CLI. |
| `praxis-fernet-key` | Symmetric envelope encryption for candidate data & cached tokens | 90 days | Fernet `MultiFernet([new_key, old_key])` decrypts with both keys, encrypts only with new key. | Rotate primary key; trigger background re-encryption worker. |
| `praxis-gemini-api-key` | Google Generative AI API key | 90 days | Create new API key in Google Cloud Console; update secret version. | Delete compromised key in Google Cloud Console. |
| `praxis-groq-api-key` | Groq LLM API key | 90 days | Create replacement key on Groq console; update secret version. | Delete compromised key on Groq console. |

---

## 3. Past Leaked Key Remediation Record

- **Finding:** A previously reported leaked Gemini API key was detected in developer `.env`.
- **Status:** Commented out and neutralized. Replaced with valid authorized credentials.
- **Verification:** `scripts/check_no_fake_data.py` and secret scanners confirm zero unredacted production tokens in repository files.
