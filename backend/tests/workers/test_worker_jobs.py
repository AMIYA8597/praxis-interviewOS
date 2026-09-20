import pytest
import asyncio

@pytest.mark.asyncio
async def test_worker_retention_duplicate_gone():
    try:
        from backend.worker_settings import enforce_retention_policies_job
        assert False, "enforce_retention_policies_job should not exist"
    except ImportError:
        pass
