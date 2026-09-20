import asyncio
import httpx
from backend.app.main import create_app
import sys
import traceback

app = create_app()

async def run_tests():
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Auth
            print("Testing /api/v1/auth/me")
            r = await client.get("/api/v1/auth/me")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"
            
            # study
            r = await client.get("/api/v1/study/materials")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

            # outreach
            r = await client.get("/api/v1/outreach/campaigns")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

            # applications
            r = await client.get("/api/v1/applications")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

            # analytics
            r = await client.get("/api/v1/analytics/dashboard")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

            # admin
            r = await client.get("/api/v1/admin/users")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

            print("All router smoke tests passed (unauthorized endpoints behave as expected)")
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
