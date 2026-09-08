import os
import shutil
from typing import Protocol

class ObjectStorage(Protocol):
    async def save(self, file_content: bytes, filename: str, path: str) -> str: ...
    async def load(self, file_uri: str) -> bytes: ...

class LocalFileStorage:
    def __init__(self, base_dir: str = "/tmp/praxis_storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def save(self, file_content: bytes, filename: str, path: str) -> str:
        full_path = os.path.join(self.base_dir, path, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_content)
        return f"file://{full_path}"

    async def load(self, file_uri: str) -> bytes:
        if not file_uri.startswith("file://"):
            raise ValueError("Invalid local URI")
        path = file_uri.replace("file://", "")
        with open(path, "rb") as f:
            return f.read()

class SupabaseStorage:
    def __init__(self):
        # Requires Supabase Python Client
        pass

    async def save(self, file_content: bytes, filename: str, path: str) -> str:
        # Stub
        return f"supabase://bucket/{path}/{filename}"

    async def load(self, file_uri: str) -> bytes:
        return b""

def get_storage_client() -> ObjectStorage:
    mode = os.environ.get("STORAGE_BACKEND", "local")
    if mode == "supabase":
        return SupabaseStorage()
    return LocalFileStorage()
