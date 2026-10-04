"""
Object storage backends.

Objects are addressed by a *relative key* such as
"<candidate_id>/resumes/<document_id>/<safe_filename>". Keys are always
namespaced by candidate id (enforced by the caller) and validated here so a
crafted key cannot escape the storage root.
"""
import asyncio
import logging
import os
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class StorageError(Exception):
    pass


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


def validate_key(key: str) -> str:
    """Reject absolute paths, traversal and odd characters."""
    if not key or "\\" in key or "\x00" in key:
        raise StorageError("Invalid storage key")
    p = PurePosixPath(key)
    if p.is_absolute() or any(part in ("..", ".", "") for part in p.parts):
        raise StorageError("Invalid storage key")
    return str(p)


def _legacy_uri_to_key(key: str) -> str:
    # Older rows stored "file://<abs path>" URIs; keep them readable.
    return key[len("file://"):] if key.startswith("file://") else key


class LocalFileStorage:
    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = _legacy_uri_to_key(key)
        candidate = Path(key)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.base_dir / validate_key(key)).resolve()
        if self.base_dir not in resolved.parents and resolved != self.base_dir:
            raise StorageError("Storage key escapes storage root")
        return resolved

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)

        def _write():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".part")
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)

        await asyncio.to_thread(_write)
        return validate_key(key)

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as e:
            raise StorageError("Object not found") from e

    async def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            await asyncio.to_thread(path.unlink)
        except FileNotFoundError:
            pass

    # Backwards-compatible names used by older call sites.
    async def save(self, file_content: bytes, filename: str, path: str) -> str:
        return await self.put(f"{path.strip('/')}/{filename}", file_content)

    async def load(self, file_uri: str) -> bytes:
        return await self.get(file_uri)


class SupabaseStorage:
    """Supabase Storage via its REST API using the service-role key (server side only)."""

    def __init__(self, url: str, service_key: str, bucket: str = "documents", timeout: float = 30.0):
        if not url or not service_key:
            raise StorageError("Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        self.base = f"{url.rstrip('/')}/storage/v1/object/{bucket}"
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self.timeout = timeout

    def _url(self, key: str) -> str:
        return f"{self.base}/{quote(validate_key(key))}"

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        headers = {**self.headers, "Content-Type": content_type, "x-upsert": "true"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._url(key), content=data, headers=headers)
        if resp.status_code >= 300:
            raise StorageError(f"Supabase upload failed with status {resp.status_code}")
        return validate_key(key)

    async def get(self, key: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(key), headers=self.headers)
        if resp.status_code == 404:
            raise StorageError("Object not found")
        if resp.status_code >= 300:
            raise StorageError(f"Supabase download failed with status {resp.status_code}")
        return resp.content

    async def delete(self, key: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(self._url(key), headers=self.headers)
        if resp.status_code not in (200, 204, 404):
            raise StorageError(f"Supabase delete failed with status {resp.status_code}")

    async def save(self, file_content: bytes, filename: str, path: str) -> str:
        return await self.put(f"{path.strip('/')}/{filename}", file_content)

    async def load(self, file_uri: str) -> bytes:
        return await self.get(file_uri)


def get_storage_client() -> ObjectStorage:
    from packages.config.settings import settings

    if settings.STORAGE_BACKEND.lower() == "supabase":
        return SupabaseStorage(settings.SUPABASE_URL or "", settings.SUPABASE_SERVICE_ROLE_KEY or "", settings.STORAGE_BUCKET)
    return LocalFileStorage(settings.STORAGE_LOCAL_PATH)
