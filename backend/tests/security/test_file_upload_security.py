"""
PRAXIS InterviewOS — File Processing Security Regression Suite
Verifies filename path traversal defenses, magic-byte sniffing, and size limit enforcement.
"""
import io
import pytest
from fastapi import UploadFile

from backend.app.core.uploads import (
    sanitize_filename,
    sniff_mime,
    read_limited,
    validate_resume_upload,
    PDF,
    TXT,
)
from backend.app.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError


def test_path_traversal_filenames_are_sanitized():
    # Unix traversal
    assert sanitize_filename("../../../etc/cron.d/malicious.pdf") == "malicious.pdf"
    # Windows traversal
    assert sanitize_filename("..\\..\\..\\Windows\\System32\\cmd.exe.pdf") == "cmd.exe.pdf"
    # Null byte attack
    assert "\x00" not in sanitize_filename("resume\x00.pdf")


def test_unicode_normalization_in_filenames():
    raw_name = "résumé_2026.pdf"
    clean = sanitize_filename(raw_name)
    assert clean.endswith(".pdf")
    assert clean.startswith("resume_2026")


def test_magic_byte_sniffing_pdf():
    valid_pdf_header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    assert sniff_mime(valid_pdf_header) == PDF

    # Binary payload that is not a valid PDF or zip and contains null bytes
    binary_payload = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    with pytest.raises(UnsupportedMediaTypeError):
        sniff_mime(binary_payload)


@pytest.mark.asyncio
async def test_extension_content_mismatch_rejected():
    fake_pdf = b"<html><script>alert(1)</script></html>"
    upload = UploadFile(
        filename="malicious.pdf",
        file=io.BytesIO(fake_pdf),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(UnsupportedMediaTypeError) as exc_info:
        await validate_resume_upload(upload, max_bytes=1024 * 1024)
    assert "File content does not match its extension" in str(exc_info.value)


def test_magic_byte_sniffing_text():
    clean_txt = b"John Doe\nSoftware Engineer\nPython, Docker, Kubernetes"
    assert sniff_mime(clean_txt) == TXT

    binary_disguised_as_txt = b"GIF89a\x01\x00\x01\x00"
    with pytest.raises(Exception):
        sniff_mime(binary_disguised_as_txt)


@pytest.mark.asyncio
async def test_read_limited_enforces_size_ceiling():
    small_data = b"Hello world" * 10
    upload = UploadFile(filename="small.txt", file=io.BytesIO(small_data))
    result = await read_limited(upload, max_bytes=1000)
    assert result == small_data

    large_data = b"A" * 2000
    oversized_upload = UploadFile(filename="large.txt", file=io.BytesIO(large_data))
    with pytest.raises(PayloadTooLargeError):
        await read_limited(oversized_upload, max_bytes=1000)
