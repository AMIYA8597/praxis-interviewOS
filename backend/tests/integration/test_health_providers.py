import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_providers_with_and_without_key(test_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    resp = test_client.get("/api/v1/health/providers")
    print("\nWITH KEY:\n", resp.json())
    
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # The gateway config is read during lifespan or request?
    # Wait, in health.py, it reads `gateway.providers`.
    # If gateway is initialized in lifespan, the providers dict is populated once at startup based on the env.
    # We might need to manually set or delete it in the app state if it's cached, or just instantiate GatewayRouter.
    # Actually, the user says "remove or invalidate that key, restart, and confirm..."
    # The prompt explicitly says "restart".

