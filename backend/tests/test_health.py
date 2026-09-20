import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.dependencies import get_db_session, get_redis, get_ai_gateway
from unittest.mock import AsyncMock, MagicMock

class MockGateway:
    status = "not yet configured"
    providers = {}

@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_ai_gateway] = lambda: MockGateway()
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_providers_health_endpoint():
    response = client.get("/api/v1/health/providers")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
