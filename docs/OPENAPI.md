# PRAXIS OpenAPI Contract Documentation

## 1. Specification Overview

The PRAXIS API OpenAPI 3.1 specification is committed at:
```
docs/openapi.json
```
It defines all public HTTP routes mounted by the FastAPI core API application.

- **Title**: PRAXIS Backend API
- **Version**: 1.0.0
- **Total Documented Routes**: 84 endpoints
- **Authentication Security Schemes**: `HTTPBearer` (Supabase JWT)

---

## 2. Generating the OpenAPI Specification

To deterministically export the current schema from the live application routes:
```powershell
python -c "
import json
from backend.app.main import create_app

app = create_app()
schema = app.openapi()

with open('docs/openapi.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=2)

print('Exported docs/openapi.json successfully')
"
```

---

## 3. Automated Contract Drift Guard

CI enforces that `docs/openapi.json` is never out of sync with application routes via:
```powershell
pytest backend/tests/api/test_openapi_contract.py
```
This test asserts:
1. Every route in the FastAPI application is documented in `docs/openapi.json`.
2. Any undocumented route, method change, or deletion fails CI immediately.
3. Protected operational endpoints (such as `/metrics`) are intentionally excluded via `include_in_schema=False`.
