import pytest
from backend.app.core.storage import LocalFileStorage, StorageError

pytestmark = pytest.mark.asyncio


async def test_storage_put_get_delete(tmp_path):
    storage = LocalFileStorage(base_dir=str(tmp_path))
    test_key = "resumes/test_user/fake_resume.pdf"
    test_data = b"%PDF-1.4 Fake PDF content"

    uploaded_key = await storage.put(test_key, test_data, "application/pdf")
    assert uploaded_key == test_key

    retrieved_data = await storage.get(test_key)
    assert retrieved_data == test_data

    await storage.delete(test_key)

    with pytest.raises(StorageError):
        await storage.get(test_key)


async def test_local_storage_path_traversal(tmp_path):
    storage = LocalFileStorage(base_dir=str(tmp_path))
    test_data = b"malicious content"

    with pytest.raises(StorageError):
        await storage.put("../resumes/hack.txt", test_data, "text/plain")

    with pytest.raises(StorageError):
        await storage.put("/etc/passwd", test_data, "text/plain")
