import json
import pathlib

from backend.app.main import create_app


def test_openapi_schema_matches_routes():
    """Verify that committed docs/openapi.json matches live application routes."""
    app = create_app()
    live_schema = app.openapi()
    
    root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
    spec_path = root / "docs" / "openapi.json"
    
    assert spec_path.exists(), f"OpenAPI specification not found at {spec_path}"
    with open(spec_path, "r", encoding="utf-8") as f:
        committed_schema = json.load(f)
        
    live_paths = set(live_schema.get("paths", {}).keys())
    committed_paths = set(committed_schema.get("paths", {}).keys())
    
    undocumented = live_paths - committed_paths
    assert not undocumented, f"Found undocumented routes not present in committed openapi.json: {undocumented}"
    
    # Verify operations match
    for path in live_paths:
        live_ops = set(live_schema["paths"][path].keys())
        committed_ops = set(committed_schema["paths"][path].keys())
        missing_ops = live_ops - committed_ops
        assert not missing_ops, f"Route {path} has undocumented operations: {missing_ops}"
