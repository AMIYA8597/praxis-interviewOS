import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.dependencies import get_current_candidate, get_ai_gateway

class MockDB:
    async def execute(self, query, params=None):
        class MockResult:
            def fetchall(self):
                class MockRow:
                    def __init__(self, mapping):
                        self._mapping = mapping
                return [MockRow({"id": "item1", "topic": "Python", "source": "manual", "prompt": "test", "reference_answer": "ans", "difficulty": "easy", "created_at": "2023-01-01", "next_review_at": None})]
        return MockResult()

class MockGateway:
    db = MockDB()

async def override_get_current_candidate():
    return {"id": "test-candidate-123"}

async def override_get_ai_gateway():
    return MockGateway()

app.dependency_overrides[get_current_candidate] = override_get_current_candidate
app.dependency_overrides[get_ai_gateway] = override_get_ai_gateway

client = TestClient(app)

def test_get_study_materials():
    response = client.get("/api/v1/study/materials")
    assert response.status_code == 200
    data = response.json()
    assert "materials" in data
    assert len(data["materials"]) == 1
    assert data["materials"][0]["id"] == "item1"

def test_generate_study_material():
    req_data = {"topic": "FastAPI", "difficulty": "Hard"}
    r1 = client.post("/api/v1/study/generate", json=req_data)
    r2 = client.post("/api/v1/study/generate", json=req_data)
    
    assert r1.status_code == 200
    assert r2.status_code == 200
    
    d1 = r1.json()
    d2 = r2.json()
    
    assert d1["status"] == "queued"
    assert d2["status"] == "queued"
    assert d1["task_id"] != d2["task_id"]
    assert d1["task_id"] != "stub_task_id"
