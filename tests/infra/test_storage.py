import os
import pytest
import asyncio
from backend.storage import get_storage
from backend.storage.local import LocalFilesystemStorage

pytestmark = pytest.mark.asyncio

async def test_storage_put_get_delete():
    storage = get_storage()
    test_key = "resumes/test_user/fake_resume.pdf"
    test_data = b"%PDF-1.4 Fake PDF content"
    
    # 1. Put
    uploaded_key = await storage.put(test_key, test_data, "application/pdf")
    assert uploaded_key == test_key
    
    # 2. Get byte-identical
    retrieved_data = await storage.get(test_key)
    assert retrieved_data == test_data
    
    # 3. Signed URL 
    url = await storage.signed_url(test_key, expires_in_s=2)
    assert url is not None
    assert isinstance(url, str)
    assert len(url) > 0
    
    if url.startswith("http"):
        import httpx
        # It should work immediately
        resp = httpx.get(url)
        assert resp.status_code == 200, "Signed URL should be accessible"
        
        # Wait for expiry
        await asyncio.sleep(3)
        
        # It should be denied now
        resp_expired = httpx.get(url)
        assert resp_expired.status_code in (400, 401, 403), "Signed URL did not expire!"
    
    # 4. Delete
    await storage.delete(test_key)
    
    # 5. Confirm Get raises error
    with pytest.raises(FileNotFoundError):
        await storage.get(test_key)

async def test_local_storage_path_traversal():
    # Only applies to LocalFilesystemStorage
    if os.environ.get("STORAGE_BACKEND", "local").lower() != "local":
        pytest.skip("Path traversal test is specific to local storage implementation")
        
    storage = get_storage()
    assert isinstance(storage, LocalFilesystemStorage)
    
    test_data = b"malicious content"
    
    with pytest.raises(ValueError, match="Invalid key"):
        await storage.put("../resumes/hack.txt", test_data, "text/plain")
        
    with pytest.raises(ValueError, match="Invalid key"):
        await storage.put("/etc/passwd", test_data, "text/plain")
