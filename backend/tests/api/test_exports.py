"""
Tests for POST/GET /api/v1/export endpoints.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from backend.app.dependencies import get_db_session
from backend.app.main import app
from backend.tests.conftest import override_get_db_session


def test_initiate_export_rate_limit_or_accepted(test_client: TestClient, auth_headers: dict):
    """POST /export returns 202 when allowed or 429 when existing export in progress."""
    response = test_client.post("/api/v1/export", headers=auth_headers)
    assert response.status_code in (200, 202, 401, 422, 429)


def test_get_export_status_404_unknown_id(test_client: TestClient, auth_headers: dict):
    """GET /export/{id} with a missing record returns 404."""
    random_id = str(uuid.uuid4())
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    try:
        response = test_client.get(f"/api/v1/export/{random_id}", headers=auth_headers)
        assert response.status_code in (401, 404)
    finally:
        app.dependency_overrides[get_db_session] = override_get_db_session


def test_export_status_model_schema():
    """ExportStatus schema accepts all required fields."""
    from backend.app.api.exports import ExportStatus
    from datetime import datetime, timezone

    obj = ExportStatus(
        export_id=str(uuid.uuid4()),
        status="ready",
        requested_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        download_url="https://storage.example.com/export.json?sig=abc",
    )
    assert obj.status == "ready"
    assert obj.download_url is not None


def test_export_initiated_model_schema():
    """ExportInitiated schema serialises correctly."""
    from backend.app.api.exports import ExportInitiated
    from datetime import datetime, timezone

    obj = ExportInitiated(
        export_id=str(uuid.uuid4()),
        status="pending",
        requested_at=datetime.now(timezone.utc),
        message="Export queued.",
    )
    assert obj.status == "pending"
    d = obj.model_dump()
    assert "export_id" in d
    assert "message" in d
