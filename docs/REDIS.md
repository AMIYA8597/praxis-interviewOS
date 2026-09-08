# Redis Architecture & Roles

Redis serves four distinct roles in PRAXIS. To ensure our single free-tier instance doesn't become an unmanageable, unbounded blob of memory, we strictly enforce namespace separation and mandatory Time-To-Live (TTL) expiration.

## 1. Key Namespace Convention

All keys must adhere to one of the following four prefixes:

- `cache:*`: Cached, regenerable data (e.g., embeddings cache, provider health snapshots, parsed metadata). **Explicit TTL required.** Nothing in this namespace is the only copy of anything.
- `queue:*`: Reserved exclusively for `arq` background job queues. Arq manages this namespace natively. Do not write to this namespace manually.
- `session:*`: Ephemeral realtime session state. Used by the Stage 2/3 realtime agent for in-flight session context (e.g., streaming transcription buffers, uncommitted conversational turns). **Explicit TTL required.** This is a fast working set, not the system of record. Postgres `session_state_log` remains the system of record.
- `ratelimit:*`: Fixed-window counters for rate-limiting. See below.

**Mandatory TTL Discipline**: Every `SET` operation to `cache:*` or `session:*` must include an explicit TTL. The `redis_client.py` wrapper strictly enforces this and raises an error if an unbounded SET is attempted. An unbounded key is a slow, silent memory leak that will eventually crash the instance.

## 2. Rate Limiting Scheme

Rate limiting uses a fixed-window token bucket approach. The key shape is:
`ratelimit:<scope>:<identifier>:<window>`
*(e.g., `ratelimit:api:user_abc123:60s`)*

**Data Structure**: Each key stores an integer counter. The TTL is set exactly to the window length when the key is first created, resetting naturally upon expiry.

*Tradeoff Note*: We use a fixed-window counter because it is simple, fast, and requires minimal Redis operations compared to a true sliding-window or leaky-bucket implementation. At our current scale, the slight inaccuracy at the window boundaries (e.g., bursting at the 59th and 61st second) is acceptable. Upgrading to a sliding window is a documented deferred improvement.

## 3. Local and Hosted Redis Parity

- **Local Dev**: Handled by the local Docker stack (`redis:7-alpine`).
- **Hosted Demo**: Uses Upstash Redis (Free Tier).
- **Parity**: Both are accessed via the standard `REDIS_URL` pattern. The application layer makes zero distinction between them.

*Upstash Free Tier Limits (Current Validation)*:
Upstash provides a maximum of 10,000 requests per day, a 256MB memory cap, and a strict limit of 10,000 concurrent connections on the free tier. Native Redis protocol over TLS is fully supported, allowing the standard `redis.asyncio` client to connect identically to both local and Upstash instances.

## 4. Connection Pooling Configuration

Redis connections are finite, especially on free-tier services. If the API, background workers, and realtime agent all spawn unbounded connection pools, the service will hit `maxclients` limits silently.

**Pool Sizing Rules**:
- **Core API & Workers**: Share a connection pool sized strictly to expected concurrent request volume.
- **Realtime Agent (Stage 2/3)**: Holds a very small number of long-lived connections for sub/pub or fast polling session state.
- **Concrete Limit**: In local development and early stage deployment, the global `max_connections` pool limit is capped at **10 connections** per service instance. We will revisit this boundary during Phase 1.15's load testing.
