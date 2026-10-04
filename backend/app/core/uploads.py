"""
Upload validation: size limit (streamed), extension allow-list, magic-byte
sniffing and filename sanitisation. Never trust the client's Content-Type
or extension alone.
"""
import io
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass

from fastapi import UploadFile

from backend.app.exceptions import BadRequestError, PayloadTooLargeError, UnsupportedMediaTypeError

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT = "text/plain"

EXTENSIONS = {".pdf": PDF, ".docx": DOCX, ".txt": TXT}
# Client-declared types we tolerate per detected type (browsers vary).
ACCEPTED_DECLARED = {
    PDF: {PDF, "application/x-pdf", "application/octet-stream", ""},
    DOCX: {DOCX, "application/zip", "application/octet-stream", ""},
    TXT: {TXT, "application/octet-stream", ""},
}
_READ_CHUNK = 64 * 1024


@dataclass
class ValidatedUpload:
    data: bytes
    mime_type: str
    safe_filename: str
    size: int


def sanitize_filename(filename: str, default_ext: str = "") -> str:
    """Strip paths/control chars, normalise, and cap length."""
    name = os.path.basename((filename or "").replace("\\", "/"))
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    stem, ext = os.path.splitext(name)
    stem = stem.strip("._-")[:100] or "upload"
    ext = (ext or default_ext).lower()[:10]
    return f"{stem}{ext}"


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks, failing fast with 413 once over the limit."""
    buf = bytearray()
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise PayloadTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
    return bytes(buf)


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return PDF
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
            if "word/document.xml" in names and "[Content_Types].xml" in names:
                return DOCX
        except zipfile.BadZipFile:
            pass
        raise UnsupportedMediaTypeError("ZIP archive is not a valid DOCX document")
    if b"\x00" not in data[:8192]:
        try:
            data[:65536].decode("utf-8")
            return TXT
        except UnicodeDecodeError:
            pass
    raise UnsupportedMediaTypeError("Unsupported file type. Only PDF, DOCX and TXT are allowed.")


async def validate_resume_upload(file: UploadFile, max_bytes: int) -> ValidatedUpload:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXTENSIONS:
        raise UnsupportedMediaTypeError("Unsupported file type. Only PDF, DOCX and TXT are allowed.")
    data = await read_limited(file, max_bytes)
    if not data:
        raise BadRequestError("Uploaded file is empty", code="empty_file")
    detected = sniff_mime(data)
    if detected != EXTENSIONS[ext]:
        raise UnsupportedMediaTypeError("File content does not match its extension")
    declared = (file.content_type or "").split(";")[0].strip().lower()
    if declared not in ACCEPTED_DECLARED[detected]:
        raise UnsupportedMediaTypeError("Declared content type does not match file content")
    return ValidatedUpload(
        data=data, mime_type=detected, safe_filename=sanitize_filename(file.filename or "", ext), size=len(data)
    )
