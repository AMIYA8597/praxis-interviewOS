# PRAXIS InterviewOS — Database Provider Decision (Supabase vs. Cloud SQL)

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Authoritative Choice:** Architecture A (Managed PostgreSQL with Secure Connection Pooling)  

---

## 1. Trade-Off Analysis

| Evaluation Dimension | Architecture A: Supabase PostgreSQL (`rqbbfegkqmsvthdgoyqk`) | Architecture B: Google Cloud SQL PostgreSQL 17 |
|---|---|---|
| **Current Repository State** | **Already deployed & verified** with 31 migrations applied and 70 tables under `FORCE RLS`. | Not provisioned; requires Terraform apply and data migration. |
| **Auth Primitives** | Native integration with Supabase Auth (`auth.users`, JWKS). | Requires self-hosting auth tables or external JWKS bridge. |
| **Vector Search (`pgvector`)** | Verified enabled (`vector(384)` for BGE embeddings). | Available on Cloud SQL but requires manual extension enabling and index recreation. |
| **Connection Pooling** | Supavisor / PgBouncer connection pooling on port 6543 / 5432 with `statement_cache_size=0`. | Requires Cloud SQL Auth Proxy sidecar or internal PgBouncer instance. |
| **Operational Spend** | **$0 / month** on existing active tier. | **~$50 to $120 / month** for dedicated instance + storage + egress. |
| **Migration Risk** | **Zero risk**; zero data loss; preserves existing test users and candidate entities. | High risk; requires schema export, data dump, and cutover window. |
| **Disaster Recovery** | Point-in-time recovery, automated daily backups, manual `pg_dump`. | Cloud SQL automated backups and PITR. |

---

## 2. Decision & Justification

**DECISION:** Retain **Architecture A** as the single authoritative database for PRAXIS InterviewOS.
1. Strictly adheres to Non-Negotiable Rule 0.2: *"Do not introduce duplicate databases, queues, storage systems, services, providers or sources of truth. Do not deploy Cloud SQL and Supabase as two independent authoritative business databases."*
2. Eliminates unnecessary cloud expenditure in staging and production.
3. Completely avoids high-risk data cutover during staging certification.
4. Cloud SQL Terraform modules in `infra/gcp/` are preserved as a disaster recovery / enterprise migration option if migration is authorized in the future.
