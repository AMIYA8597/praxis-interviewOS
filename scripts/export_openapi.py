#!/usr/bin/env python3
"""Export the PRAXIS API OpenAPI schema as JSON.

Usage:
    python scripts/export_openapi.py > openapi.json
    python scripts/export_openapi.py --output docs/openapi.json

The Vercel frontend can fetch this at runtime from /api/v1/openapi.json
when API docs are enabled, or use this script to generate a static copy
for client SDK generation (e.g. openapi-typescript-codegen).
"""
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Export PRAXIS OpenAPI schema")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    import os, pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./noop.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("LOCAL_ONLY_MODE", "true")

    from backend.app.main import create_app
    app = create_app()
    schema = app.openapi()

    output = json.dumps(schema, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"OpenAPI schema written to {args.output}", file=sys.stderr)
    else:
        print(output)

if __name__ == "__main__":
    main()
