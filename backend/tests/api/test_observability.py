import base64
import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.core.logging_config import StructuredFormatter, _redact
from backend.app.dependencies import get_ai_gateway, get_db_session, get_redis
from backend.app.main import app
from packages.config.settings import settings


@pytest.fixture
def test_client():
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    mock_gateway = MagicMock()
    mock_gateway.providers = {}

    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_ai_gateway] = lambda: mock_gateway

    client = TestClient(app)
    yield client, mock_db, mock_redis
    app.dependency_overrides.clear()


def test_health_live_endpoint(test_client):
    client, _, _ = test_client
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready_healthy(test_client):
    client, mock_db, mock_redis = test_client
    mock_db.execute.return_value = None
    mock_redis.ping.return_value = True

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_health_ready_db_down(test_client):
    client, mock_db, mock_redis = test_client
    mock_db.execute.side_effect = ConnectionError("DB connection refused")
    mock_redis.ping.return_value = True

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()["detail"]
    assert data["status"] == "not_ready"
    assert "database" in data["components"]


def test_health_ready_redis_down(test_client):
    client, mock_db, mock_redis = test_client
    mock_db.execute.return_value = None
    mock_redis.ping.side_effect = ConnectionError("Redis unreachable")

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()["detail"]
    assert data["status"] == "not_ready"
    assert "redis" in data["components"]


def test_health_startup_all_applied(test_client):
    client, mock_db, _ = test_client
    from scripts.migrate import migration_files

    all_migrations = [f.name for f in migration_files()]
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(m,) for m in all_migrations]
    mock_db.execute.return_value = mock_result

    resp = client.get("/health/startup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["migrations_current"] is True
    assert data["applied_count"] == len(all_migrations)


def test_health_startup_pending_migrations(test_client):
    client, mock_db, _ = test_client
    mock_result = MagicMock()
    # Simulate an empty or partially migrated DB
    mock_result.fetchall.return_value = [("20260907235759_local_auth_primitives.sql",)]
    mock_db.execute.return_value = mock_result

    resp = client.get("/health/startup")
    assert resp.status_code == 503
    data = resp.json()["detail"]
    assert data["status"] == "not_ready"
    assert data["pending_count"] > 0


def test_metrics_rejects_unauthenticated(test_client):
    client, _, _ = test_client
    resp = client.get("/metrics")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_metrics_rejects_bad_credentials(test_client):
    client, _, _ = test_client
    bad_auth = base64.b64encode(b"wrong_user:wrong_pass").decode("utf-8")
    resp = client.get("/metrics", headers={"Authorization": f"Basic {bad_auth}"})
    assert resp.status_code == 401


def test_metrics_accepts_valid_basic_auth(test_client):
    client, _, _ = test_client
    user = settings.METRICS_USER or "prometheus"
    password = settings.METRICS_PASSWORD or "praxis_metrics_token"
    auth_str = f"{user}:{password}"
    valid_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    resp = client.get("/metrics", headers={"Authorization": f"Basic {valid_auth}"})
    assert resp.status_code == 200
    assert "praxis_" in resp.text


def test_metrics_accepts_valid_bearer_token(test_client):
    client, _, _ = test_client
    token = settings.METRICS_PASSWORD or "praxis_metrics_token"
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "praxis_" in resp.text


def test_correlation_ids_in_response_headers(test_client):
    client, _, _ = test_client
    req_id = "test-request-id-12345678"
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

    resp = client.get(
        "/health/live",
        headers={"X-Request-ID": req_id, "X-Trace-ID": trace_id},
    )
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == req_id
    assert resp.headers["X-Trace-ID"] == trace_id


def test_structured_json_logging_with_correlation():
    formatter = StructuredFormatter(service="praxis-test")
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Synthetic request executed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-obs-11111111"
    record.trace_id = "trace-obs-22222222"
    record.user_id = "user-obs-33333333"
    record.session_id = "sess-obs-44444444"

    raw_json = formatter.format(record)
    data = json.loads(raw_json)

    assert data["service"] == "praxis-test"
    assert data["level"] == "INFO"
    assert data["message"] == "Synthetic request executed"
    assert data["request_id"] == "req-obs-11111111"
    assert data["trace_id"] == "trace-obs-22222222"
    assert data["user_id"] == "user-obs-33333333"
    assert data["session_id"] == "sess-obs-44444444"
    assert "timestamp" in data


def test_pii_and_credential_masking():
    sensitive_dict = {
        "api_key": "sk-secret-12345",
        "access_token": "eyJh...super-secret-jwt",
        "email": "candidate@example.com",
        "user_email": "real_person@gmail.com",
        "phone_number": "+1-555-0199",
        "password": "SuperSecretPassword123!",
        "safe_field": "interview_preparation_session",
    }
    redacted = _redact("payload", sensitive_dict)
    assert redacted["api_key"].startswith("<redacted")
    assert redacted["access_token"].startswith("<redacted")
    assert redacted["email"].startswith("<redacted")
    assert redacted["user_email"].startswith("<redacted")
    assert redacted["phone_number"].startswith("<redacted")
    assert redacted["password"].startswith("<redacted")
    assert redacted["safe_field"] == "interview_preparation_session"
