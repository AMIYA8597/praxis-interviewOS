import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_profile_deletion():
    # Create profile -> candidate -> projects -> sessions
    # Delete profile
    # Assert everything deleted (cascade)
    pass
