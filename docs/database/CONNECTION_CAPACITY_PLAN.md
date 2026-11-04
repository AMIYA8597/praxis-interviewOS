# PRAXIS InterviewOS — Database Connection Capacity Plan

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Connection Budget & Sizing

| Client Component | Max Instances | Pool Size per Instance | Max Overflow | Max Concurrent Connections |
|---|---|---|---|---|
| **API (`praxis-api`)** | 3 (staging) / 10 (prod) | 5 | 5 | 30 (staging) / 100 (prod) |
| **Realtime (`praxis-realtime`)** | 2 (staging) / 10 (prod) | 3 | 2 | 10 (staging) / 50 (prod) |
| **Worker (`praxis-worker`)** | 1 (staging) / 5 (prod) | 5 | 5 | 10 (staging) / 50 (prod) |
| **Direct Management / CI** | 2 | 1 | 0 | 2 |
| **Total Connections Required** | — | — | — | **52 (staging) / 202 (prod)** |

---

## 2. Pooler Configuration Rules

1. **Transaction Pooling Mode:** When connecting through Supavisor / PgBouncer (port 6543), connection mode is set to `transaction`.
2. **Prepared Statements Disabled:** `backend/app/db/session.py` explicitly sets:
   ```python
   connect_args = {
       "statement_cache_size": 0,
       "prepared_statement_cache_size": 0,
   }
   ```
   This prevents `prepared statement "..." already exists` errors across pooled connections.
3. **Pre-Ping & Recycling:**
   - `pool_pre_ping = True` ensures dead or closed TCP connections are discarded before issuing queries.
   - `pool_recycle = 1800` (30 minutes) recycles idle connections periodically.
   - `statement_timeout = 30000` (30s) aborts runaway queries.
