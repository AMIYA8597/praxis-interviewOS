# SERVICE ROLE GUIDE

## When to use service role (admin operations only)
The Supabase Service Role key bypasses all Row-Level Security (RLS) policies. It must only be used in trusted backend contexts for administrative operations.

Use the service role for:
- Database migrations and schema modifications
- Webhook handlers that verify external events (e.g., Stripe, Clerk)
- Scheduled background jobs that operate across multiple tenants (e.g., global retention purges)
- Administrative dashboards (when the user is verified as an admin)
- System-level operations that don't belong to a specific user

## How to request data as service role
In the FastAPI backend, you should use a dedicated database session or connection that is not bound to a user's JWT.

```python
# Example of executing a query as service role (assuming standard connection doesn't set JWT claim)
async with get_service_role_db() as db:
    # This query will see all rows, bypassing RLS
    await db.execute("SELECT * FROM profiles")
```

If you are using the Supabase python client:
```python
from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```

## Audit logging for service role usage
All actions performed using the service role that modify user data must be explicitly logged to the `audit_logs` table.

```python
# Example audit log insertion
await db.execute(
    "INSERT INTO audit_logs (action, resource, details) VALUES (:action, :resource, :details)",
    {"action": "global_purge", "resource": "documents", "details": '{"count": 100}'}
)
```

## Never expose service role key to frontend
- **CRITICAL**: The `SUPABASE_SERVICE_ROLE_KEY` must never be exposed to the frontend (e.g., React/Vite app).
- It must never be included in the `.env.local` or prefixed with `VITE_`.
- If the service role key is leaked, the entire database is compromised.
