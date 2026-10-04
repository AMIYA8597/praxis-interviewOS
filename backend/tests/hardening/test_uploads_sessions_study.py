import io
import zipfile

import pytest
from sqlalchemy import text

from packages.config.settings import settings


def _docx_bytes(body: str = "Senior engineer. Python and Go.") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p></w:body></w:document>",
        )
    return buf.getvalue()


# ── Resume upload: validation ────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,content,ctype",
    [
        ("malware.exe", b"MZ\x90\x00binary", "application/octet-stream"),
        ("resume.png", b"\x89PNG\r\n\x1a\nxxxx", "image/png"),
        ("fake.pdf", b"MZ\x90\x00not really a pdf\x00\x00", "application/pdf"),   # extension spoofing
        ("fake.docx", b"PK\x03\x04garbage-not-a-zip", DOCX_CT := "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("resume.pdf", b"plain text pretending to be pdf", "application/pdf"),       # magic mismatch
        ("resume.txt", b"%PDF-1.7 real pdf named txt", "text/plain"),             # content/extension mismatch
        ("resume.txt", b"hello", "application/pdf"),                              # declared type mismatch
    ],
)
async def test_resume_upload_rejects_bad_types(api, alice, arq_pool, filename, content, ctype):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/resumes", files={"file": (filename, content, ctype)})
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "unsupported_file_type"
    assert arq_pool.jobs == []


@pytest.mark.asyncio
async def test_resume_upload_empty_file_is_400(api, alice):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/resumes", files={"file": ("cv.txt", b"", "text/plain")})
    assert resp.status_code == 400 and resp.json()["code"] == "empty_file"


@pytest.mark.asyncio
async def test_resume_upload_size_limit_is_413(api, alice, arq_pool, monkeypatch):
    client, act_as = api
    act_as(alice)
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 2048)
    resp = await client.post("/resumes", files={"file": ("cv.txt", b"a" * 5000, "text/plain")})
    assert resp.status_code == 413, resp.text
    assert resp.json()["code"] == "payload_too_large"
    assert arq_pool.jobs == []


def test_default_upload_limit_is_10mb():
    assert settings.MAX_UPLOAD_BYTES == 10 * 1024 * 1024


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,content,ctype",
    [
        ("cv.pdf", b"%PDF-1.4\n%fake but valid header\n", "application/pdf"),
        ("cv.docx", _docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("cv.txt", "Ünïcode résumé text".encode("utf-8"), "text/plain"),
    ],
)
async def test_resume_upload_accepts_valid_types_and_enqueues_job(api, alice, arq_pool, storage, db_factory, filename, content, ctype):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/resumes", files={"file": (filename, content, ctype)})
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "uploading" and body["processing_status"] == "uploading"

    # Background job triggered (upload does not parse inline).
    assert len(arq_pool.jobs) == 1
    job = arq_pool.jobs[0]
    assert job.name == "process_resume"
    assert job.args == (body["document_id"],)
    assert job.kwargs["_job_id"] == f"process_resume:{body['document_id']}"
    assert "trace_carrier" in job.kwargs

    # Stored under the owner's namespace, sanitized, and byte-identical.
    async with db_factory() as s:
        row = (await s.execute(text("SELECT storage_path, candidate_id, size_bytes, mime_type FROM documents WHERE id = :d"),
                               {"d": body["document_id"]})).first()
    assert row.storage_path.startswith(f"{alice['id']}/resumes/{body['document_id']}/")
    assert str(row.candidate_id) == alice["id"]
    assert row.size_bytes == len(content)
    assert await storage.get(row.storage_path) == content


@pytest.mark.asyncio
async def test_resume_filename_is_sanitized(api, alice, db_factory):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/resumes", files={"file": ("../../etc/pa ss<wd>.txt", b"hello world", "text/plain")})
    assert resp.status_code == 202
    async with db_factory() as s:
        path = (await s.execute(text("SELECT storage_path FROM documents WHERE id = :d"),
                                {"d": resp.json()["document_id"]})).scalar()
    assert ".." not in path and "<" not in path and " " not in path
    assert path.endswith("/pa_ss_wd.txt")


@pytest.mark.asyncio
async def test_legacy_upload_path_still_works(api, alice):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/resumes/upload", files={"file": ("cv.txt", b"hello", "text/plain")})
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_upload_when_queue_down_is_503_and_marks_document_failed(api, alice, db_factory):
    from backend.app.dependencies import get_arq_pool
    from backend.app.main import app

    client, act_as = api
    act_as(alice)
    app.dependency_overrides[get_arq_pool] = lambda: None
    resp = await client.post("/resumes", files={"file": ("cv.txt", b"hello", "text/plain")})
    assert resp.status_code == 503 and resp.json()["retryable"] is True
    async with db_factory() as s:
        status = (await s.execute(text("SELECT processing_status FROM documents"))).scalar()
    assert status == "failed"


# ── Sessions ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_creation_returns_session_id(api, alice):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/sessions", json={"focus_area": "system design", "interview_type": "system_design"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["session_id"] == body["id"]
    assert body["status"] == "pending" and body["candidate_id"] == alice["id"]

    fetched = await client.get(f"/sessions/{body['session_id']}")
    assert fetched.status_code == 200 and fetched.json()["focus_area"] == "system design"


@pytest.mark.asyncio
async def test_session_create_accepts_desktop_payload(api, alice):
    """The desktop client posts {"target_job_id": null} and reads `session_id`."""
    client, act_as = api
    act_as(alice)
    resp = await client.post("/sessions", json={"target_job_id": None})
    assert resp.status_code == 201 and resp.json()["session_id"]


@pytest.mark.asyncio
async def test_session_validation_rejects_bad_enum(api, alice):
    client, act_as = api
    act_as(alice)
    resp = await client.post("/sessions", json={"difficulty": "impossible"})
    assert resp.status_code == 422 and resp.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_end_session_queues_debrief(api, alice, arq_pool):
    client, act_as = api
    act_as(alice)
    sid = (await client.post("/sessions", json={})).json()["session_id"]
    resp = await client.post(f"/sessions/{sid}/end")
    assert resp.status_code == 202 and resp.json() == {"id": sid, "status": "completed", "debrief_status": "queued"}
    assert [j.name for j in arq_pool.jobs] == ["generate_session_debrief_job"]
    assert (await client.get(f"/sessions/{sid}/debrief")).json()["status"] == "pending"


@pytest.mark.asyncio
async def test_session_list_cursor_pagination(api, alice):
    client, act_as = api
    act_as(alice)
    created = [(await client.post("/sessions", json={})).json()["id"] for _ in range(5)]
    seen, cursor = [], None
    for _ in range(5):
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        page = (await client.get("/sessions", params=params)).json()
        seen += [i["id"] for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert sorted(seen) == sorted(created) and len(seen) == len(set(seen)) == 5


# ── Study / SM-2 ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sm2_review_updates_interval(api, alice, db_factory):
    client, act_as = api
    act_as(alice)
    item = (await client.post("/study/items", json={"topic": "Graphs", "prompt": "Explain Dijkstra"})).json()

    r1 = (await client.post(f"/study/items/{item['id']}/review", json={"quality": 5})).json()
    assert (r1["interval_days"], r1["repetitions"]) == (1, 1)
    assert r1["ease_factor"] == pytest.approx(2.6)

    r2 = (await client.post(f"/study/items/{item['id']}/review", json={"quality": 5})).json()
    assert (r2["interval_days"], r2["repetitions"]) == (6, 2)

    r3 = (await client.post(f"/study/items/{item['id']}/review", json={"quality": 4})).json()
    # interval = 6 * EF(2.7 after two perfect reviews, unchanged by q=4) = 16.2 -> 16 days
    assert r3["repetitions"] == 3 and r3["interval_days"] == 16

    lapse = (await client.post(f"/study/items/{item['id']}/review", json={"quality": 1})).json()
    assert (lapse["interval_days"], lapse["repetitions"]) == (1, 0)
    assert lapse["ease_factor"] < r3["ease_factor"]

    async with db_factory() as s:
        reviews = (await s.execute(text("SELECT count(*) FROM study_reviews WHERE item_id = :i"), {"i": item["id"]})).scalar()
        stored = (await s.execute(text("SELECT interval_days, repetitions FROM study_items WHERE id = :i"), {"i": item["id"]})).first()
    assert reviews == 4 and tuple(stored) == (1, 0)

    # Not due again until the new interval elapses... except after a lapse (1 day).
    due = (await client.get("/study/items/due")).json()["items"]
    assert all(d["id"] != item["id"] for d in due)


@pytest.mark.asyncio
async def test_sm2_rejects_out_of_range_quality(api, alice):
    client, act_as = api
    act_as(alice)
    item = (await client.post("/study/items", json={"topic": "T", "prompt": "P"})).json()
    resp = await client.post(f"/study/items/{item['id']}/review", json={"quality": 7})
    assert resp.status_code == 422


# ── Error envelope ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_error_envelope_is_consistent(api, alice):
    import uuid as _uuid

    client, act_as = api
    act_as(alice)
    resp = await client.get(f"/sessions/{_uuid.uuid4()}", headers={"X-Request-ID": "req-abcdef12"})
    assert resp.status_code == 404
    body = resp.json()
    assert set(body) >= {"code", "message", "detail", "retryable", "request_id"}
    assert body["request_id"] == "req-abcdef12" == resp.headers["x-request-id"]
