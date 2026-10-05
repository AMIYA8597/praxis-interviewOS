# PRAXIS Database Connection Budget

Connection pool arithmetic for Cloud Run + Supabase PostgreSQL.

---

## Key constraint

**Supabase Free Tier**: 60 simultaneous connections  
**Supabase Pro Tier**: 200 simultaneous connections (recommended for staging/production)

Cloud Run can spin up many instances simultaneously. Each instance maintains its own connection pool. The product `instances × pool_size` must stay below Postgres `max_connections`.

---

## Connection model

Each Cloud Run service uses SQLAlchemy async pool (`asyncpg`).

| Setting | Config Key | Staging Value | Production Value |
|---|---|---|---|
| Pool size per instance | `DB_POOL_SIZE` | 2 | 2 |
| Max overflow per instance | `DB_MAX_OVERFLOW` | 3 | 3 |
| Max connections per instance | pool_size + overflow | **5** | **5** |

---

## Staging budget (Supabase Free Tier: 60 connections)

| Service | Max Instances | Max Conn/Instance | Max Total |
|---|---|---|---|
| praxis-api | 3 | 5 | 15 |
| praxis-realtime | 2 | 5 | 10 |
| praxis-worker | 1 | 5 | 5 |
| **TOTAL** | | | **30** |

**Safe margin**: 30 / 60 = **50% utilization** at max scale. ✓

If Supabase free tier restricts to 20 connections (older plans), reduce to:
- `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=1` → 2 per instance → max 12 total

---

## Production budget (Supabase Pro: 200 connections)

| Service | Max Instances | Max Conn/Instance | Max Total |
|---|---|---|---|
| praxis-api | 10 | 5 | 50 |
| praxis-realtime | 5 | 5 | 25 |
| praxis-worker | 2 | 5 | 10 |
| CI / migrations | 1 | 5 | 5 |
| **TOTAL** | | | **90** |

**Safe margin**: 90 / 200 = **45% utilization** at max scale. ✓

---

## Connection string format

Use Supabase **Supavisor session mode** (port 5432), NOT the transaction pooler (port 6543).

Why: SQLAlchemy uses prepared statements and session-scoped state that breaks under transaction pooling.

```
postgresql+asyncpg://[user].[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
```

---

## Pool recycle

Set `DB_POOL_RECYCLE_S=300` (5 minutes). Supavisor closes idle connections after ~5 minutes; this prevents stale connection errors.

Set `DB_POOL_PRE_PING=true` to detect dead connections transparently.

---

## Warning conditions

| Condition | Action |
|---|---|
| Connections > 80% of limit | Reduce `api_max_instances` or decrease pool size |
| Pool timeout errors in logs | Increase `DB_POOL_TIMEOUT_S` or reduce max instances |
| `too many connections` errors | Immediate: reduce instances. Medium-term: upgrade Supabase tier |

---

## Assumptions

1. Each Cloud Run instance is treated as a separate process with its own pool.
2. Cloud Run scales up quickly; worst-case is all max instances running simultaneously.
3. Migration scripts connect once and close immediately (counted separately above).
4. No additional admin/monitoring connections are counted.

---

*Last updated: 2026-10-05*
