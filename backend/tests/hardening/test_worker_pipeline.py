"""
Background-job tests.

Unit tests (always run): text extraction, chunking, retry/dead-letter
wrapper. Integration tests (need Postgres with CREATEDB): run the real jobs
against a throwaway database migrated with scripts/migrate.py.
"""
import io
import json
import uuid
import zipfile
from types import SimpleNamespace

import pytest
import pytest_asyncio

from backend.app.services import document_processing as dp
from backend.app.worker_tasks import PermanentJobError, job


def _pdf_with_text(text_value: str) -> bytes:
    """Build a tiny but valid single-page PDF containing `text_value`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text_value}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


def _docx(text_value: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            f'<w:p><w:r><w:t>{text_value}</w:t></w:r></w:p><w:p><w:r><w:t>Second line</w:t></w:r></w:p>'
            "</w:body></w:document>",
        )
    return buf.getvalue()


# ── Parsing / chunking ───────────────────────────────────────────────────

def test_extract_text_pdf_docx_txt():
    assert "Senior Python Engineer" in dp.extract_text(_pdf_with_text("Senior Python Engineer"), dp.PDF, "cv.pdf")
    docx_text = dp.extract_text(_docx("Built Kafka pipelines"), dp.DOCX, "cv.docx")
    assert "Built Kafka pipelines" in docx_text and "Second line" in docx_text
    assert dp.extract_text("Héllo\x00 wörld".encode(), dp.TXT, "cv.txt") == "Héllo wörld"


@pytest.mark.parametrize(
    "data,mime",
    [(b"%PDF-1.4 truncated garbage", dp.PDF), (b"PK\x03\x04nope", dp.DOCX), (b"   \n\n  ", dp.TXT), (b"x", "image/png")],
)
def test_extract_text_failures_are_permanent(data, mime):
    with pytest.raises(dp.DocumentParseError):
        dp.extract_text(data, mime, "")


def test_chunking_covers_text():
    text_value = "\n\n".join(f"Paragraph {i}. " + "Distributed systems experience. " * 20 for i in range(12))
    chunks = dp.chunk(text_value)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)
    assert "Paragraph 0." in chunks[0] and "Paragraph 11." in chunks[-1]


# ── Retry / dead-letter wrapper ──────────────────────────────────────────

class _RecordingEngine:
    def __init__(self):
        self.statements = []

    def begin(self):
        engine = self

        class _Ctx:
            async def __aenter__(self_inner):
                return SimpleNamespace(execute=engine._execute)

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()

    async def _execute(self, stmt, params=None):
        self.statements.append((str(stmt), params))


@pytest.mark.asyncio
async def test_job_wrapper_retries_then_dead_letters():
    from arq import Retry

    calls = {"n": 0}

    @job(max_tries=3)
    async def flaky(ctx, document_id):
        calls["n"] += 1
        raise ConnectionError("db blip")

    engine = _RecordingEngine()
    with pytest.raises(Retry) as r1:
        await flaky({"db_engine": engine, "job_try": 1, "job_id": "j1"}, "doc-1")
    assert r1.value.defer_score == 5000  # 5s backoff on first retry
    with pytest.raises(Retry):
        await flaky({"db_engine": engine, "job_try": 2, "job_id": "j1"}, "doc-1")
    assert engine.statements == []  # no dead letter before the final attempt

    with pytest.raises(ConnectionError):
        await flaky({"db_engine": engine, "job_try": 3, "job_id": "j1"}, "doc-1", trace_carrier={"traceparent": "x"})
    assert calls["n"] == 3
    sql, params = engine.statements[-1]
    assert "INSERT INTO failed_jobs" in sql
    assert params["name"] == "flaky" and params["jid"] == "j1" and "ConnectionError" in params["err"]
    assert "trace_carrier" not in params["args"]


@pytest.mark.asyncio
async def test_permanent_errors_are_not_retried():
    @job()
    async def bad_input(ctx):
        raise PermanentJobError("document missing")

    engine = _RecordingEngine()
    result = await bad_input({"db_engine": engine, "job_try": 1})
    assert result == {"status": "failed", "error": "document missing"}
    assert any("failed_jobs" in s for s, _ in engine.statements)


def test_all_jobs_registered():
    from backend.worker_settings import WorkerSettings

    names = {f.__name__ for f in WorkerSettings.functions}
    assert {
        "process_resume", "analyze_job", "generate_session_debrief_job", "delete_candidate_account_job",
        "generate_study_material_job", "generate_embeddings", "cleanup_old_sessions", "purge_expired_retention_data",
    } <= names
    assert WorkerSettings.retry_jobs is True


# ── Integration: real jobs against a migrated Postgres ───────────────────

@pytest_asyncio.fixture
async def pg_engine():
    import asyncpg
    from sqlalchemy.ext.asyncio import create_async_engine

    from packages.config.settings import Settings

    base = Settings().sync_database_url.rsplit("/", 1)[0]
    name = f"praxis_test_{uuid.uuid4().hex[:10]}"
    try:
        admin = await asyncpg.connect(f"{base}/postgres", timeout=3)
    except Exception as e:
        pytest.skip(f"Postgres not reachable: {type(e).__name__}")
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
    except Exception as e:
        await admin.close()
        pytest.skip(f"cannot create test database: {type(e).__name__}")
    try:
        conn = await asyncpg.connect(f"{base}/{name}")
        from scripts.migrate import apply_async

        await apply_async(conn, log=lambda m: None)
        await conn.close()
        engine = create_async_engine(f"{base.replace('postgresql://', 'postgresql+asyncpg://')}/{name}")
        yield engine
        await engine.dispose()
    finally:
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()


async def _seed_candidate(engine):
    from sqlalchemy import text

    uid, cid = str(uuid.uuid4()), str(uuid.uuid4())
    async with engine.begin() as c:
        await c.execute(text("INSERT INTO auth.users (id) VALUES (CAST(:u AS uuid))"), {"u": uid})
        await c.execute(text("INSERT INTO profiles (id) VALUES (CAST(:u AS uuid))"), {"u": uid})
        await c.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES (CAST(:c AS uuid), CAST(:u AS uuid), 'Pat')"),
                        {"c": cid, "u": uid})
    return uid, cid


class _FakeGateway:
    """Returns canned structured outputs keyed by schema name."""

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    async def route(self, task, ctx, method, *args, schema=None, **kw):
        self.calls.append((task, schema.__name__ if schema else None))
        value = self.outputs.get(schema.__name__ if schema else None)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(result=value, provider_name="fake", model="fake")


@pytest.mark.asyncio
async def test_process_resume_pipeline_end_to_end(pg_engine, tmp_path, monkeypatch):
    from sqlalchemy import text

    from backend.app.core.storage import LocalFileStorage
    from backend.app.worker_tasks import process_resume
    from praxis_ai_gateway.schemas.resume import CandidateProject, CandidateSkill, ExtractedResumeProfile

    _, cid = await _seed_candidate(pg_engine)
    storage = LocalFileStorage(str(tmp_path))
    doc_id = str(uuid.uuid4())
    key = f"{cid}/resumes/{doc_id}/cv.pdf"
    await storage.put(key, _pdf_with_text("Pat Example Staff Engineer Python Kafka"), dp.PDF)
    async with pg_engine.begin() as c:
        await c.execute(text("""
            INSERT INTO documents (id, candidate_id, kind, original_filename, storage_path, mime_type, size_bytes, processing_status)
            VALUES (CAST(:d AS uuid), CAST(:c AS uuid), 'resume', 'cv.pdf', :k, :m, 10, 'uploading')"""),
            {"d": doc_id, "c": cid, "k": key, "m": dp.PDF})
        await c.execute(text("INSERT INTO resumes (candidate_id, document_id) VALUES (CAST(:c AS uuid), CAST(:d AS uuid))"),
                        {"c": cid, "d": doc_id})

    async def fake_embed(chunks):
        return [[0.01 * (i + 1)] * 384 for i in range(len(chunks))]

    monkeypatch.setattr(dp, "embed", fake_embed)
    gateway = _FakeGateway({
        "ExtractedResumeProfile": ExtractedResumeProfile(
            skills=[CandidateSkill(name="Python", proficiency="Expert", extraction_confidence=0.9),
                    CandidateSkill(name="Kafka", proficiency="Intermediate", extraction_confidence=0.7)],
            projects=[CandidateProject(title="Event bus", summary="Kafka event bus", extraction_confidence=0.8)],
        )
    })
    ctx = {"db_engine": pg_engine, "storage": storage, "gateway": gateway, "job_try": 1, "job_id": "t"}
    result = await process_resume(ctx, doc_id)
    assert result["status"] == "ready" and result["chunks"] >= 1 and result["embedded"] and result["extracted"]

    # Idempotent: a retry replaces chunks instead of duplicating them.
    await process_resume(ctx, doc_id)

    async with pg_engine.connect() as c:
        status = (await c.execute(text("SELECT processing_status, error_message FROM documents WHERE id = CAST(:d AS uuid)"), {"d": doc_id})).first()
        chunks = (await c.execute(text("SELECT count(*), bool_and(embedding IS NOT NULL), bool_and(content_tsv IS NOT NULL) FROM document_chunks WHERE document_id = CAST(:d AS uuid)"), {"d": doc_id})).first()
        claims = (await c.execute(text("SELECT claim_type, claim_text, verified_by_user FROM resume_claims ORDER BY claim_type, claim_text"))).fetchall()
        skills = (await c.execute(text("SELECT s.name FROM candidate_skills cs JOIN skills s ON s.id = cs.skill_id WHERE cs.candidate_id = CAST(:c AS uuid) ORDER BY 1"), {"c": cid})).fetchall()
        fts = (await c.execute(text("SELECT count(*) FROM document_chunks WHERE content_tsv @@ plainto_tsquery('english', 'kafka')"))).scalar()
    assert tuple(status) == ("ready", None)
    assert chunks[0] == result["chunks"] and chunks[1] is True and chunks[2] is True
    assert [s[0] for s in skills] == ["Kafka", "Python"]
    assert any(c.claim_type == "skill" and c.claim_text == "Python" and c.verified_by_user is False for c in claims)
    assert fts >= 1


@pytest.mark.asyncio
async def test_process_resume_unparseable_file_fails_permanently(pg_engine, tmp_path):
    from sqlalchemy import text

    from backend.app.core.storage import LocalFileStorage
    from backend.app.worker_tasks import process_resume

    _, cid = await _seed_candidate(pg_engine)
    storage = LocalFileStorage(str(tmp_path))
    doc_id = str(uuid.uuid4())
    key = f"{cid}/resumes/{doc_id}/cv.pdf"
    await storage.put(key, b"%PDF-1.4 broken", dp.PDF)
    async with pg_engine.begin() as c:
        await c.execute(text("""INSERT INTO documents (id, candidate_id, kind, storage_path, mime_type, processing_status)
                                VALUES (CAST(:d AS uuid), CAST(:c AS uuid), 'resume', :k, :m, 'uploading')"""),
                        {"d": doc_id, "c": cid, "k": key, "m": dp.PDF})
    result = await process_resume({"db_engine": pg_engine, "storage": storage, "job_try": 1}, doc_id)
    assert result["status"] == "failed"
    async with pg_engine.connect() as c:
        status = (await c.execute(text("SELECT processing_status FROM documents WHERE id = CAST(:d AS uuid)"), {"d": doc_id})).scalar()
        dead = (await c.execute(text("SELECT job_name, candidate_id IS NULL FROM failed_jobs"))).fetchall()
    assert status == "failed"
    assert [d[0] for d in dead] == ["process_resume"]


@pytest.mark.asyncio
async def test_analyze_job_and_debrief_and_deletion(pg_engine, tmp_path):
    from sqlalchemy import text

    from backend.app.core.storage import LocalFileStorage
    from backend.app.services.debrief import HeadlineMetrics, SessionDebrief
    from backend.app.worker_tasks import analyze_job, delete_candidate_account_job, generate_session_debrief_job
    from praxis_ai_gateway.schemas.jd import ExtractedJobBlueprint, JobRequirement, LikelyTopic

    uid, cid = await _seed_candidate(pg_engine)
    job_id, session_id, deletion_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    async with pg_engine.begin() as c:
        await c.execute(text("""INSERT INTO jobs (id, candidate_id, company_name, role_title, raw_jd_text)
                                VALUES (CAST(:j AS uuid), CAST(:c AS uuid), 'Acme', 'SRE', 'Run Kubernetes at scale.')"""),
                        {"j": job_id, "c": cid})
        await c.execute(text("""INSERT INTO practice_sessions (id, candidate_id, job_id, status)
                                VALUES (CAST(:s AS uuid), CAST(:c AS uuid), CAST(:j AS uuid), 'completed')"""),
                        {"s": session_id, "c": cid, "j": job_id})
        await c.execute(text("INSERT INTO deletion_jobs (id, profile_id, candidate_id, status) VALUES (CAST(:d AS uuid), CAST(:u AS uuid), CAST(:c AS uuid), 'queued')"),
                        {"d": deletion_id, "u": uid, "c": cid})

    gateway = _FakeGateway({
        "ExtractedJobBlueprint": ExtractedJobBlueprint(
            role="SRE", seniority_signal="Senior",
            job_requirements=[JobRequirement(skill_text="Kubernetes", category="technical", priority="required",
                                             evidence_quote="Run Kubernetes at scale.")],
            likely_topics=[LikelyTopic(topic="Incident response", rationale="SRE")],
        ),
        "SessionDebrief": SessionDebrief(
            headline_metrics=HeadlineMetrics(average_wpm=130, average_filler_rate=0.02, average_score=0.7),
            strengths=["Clear structure"], weaknesses=["Few metrics"], flagged_claims=[], jd_coverage={"covered": ["k8s"]},
        ),
    })
    ctx = {"db_engine": pg_engine, "gateway": gateway, "job_try": 1, "storage": LocalFileStorage(str(tmp_path))}

    assert (await analyze_job(ctx, job_id))["status"] == "ready"
    assert (await analyze_job(ctx, job_id))["status"] == "ready"  # idempotent upsert
    assert (await generate_session_debrief_job(ctx, session_id))["status"] == "ready"
    assert (await generate_session_debrief_job(ctx, session_id))["status"] == "ready"  # upsert, no unique violation

    async with pg_engine.connect() as c:
        job = (await c.execute(text("SELECT processing_status, seniority_signal FROM jobs WHERE id = CAST(:j AS uuid)"), {"j": job_id})).first()
        reqs = (await c.execute(text("SELECT r.skill_text, r.priority FROM job_requirements r JOIN job_blueprints b ON b.id = r.job_blueprint_id WHERE b.job_id = CAST(:j AS uuid)"), {"j": job_id})).fetchall()
        debrief = (await c.execute(text("SELECT strengths, headline_metrics FROM session_debriefs WHERE session_id = CAST(:s AS uuid)"), {"s": session_id})).first()
    assert tuple(job) == ("ready", "Senior")
    assert [tuple(r) for r in reqs] == [("Kubernetes", "required")]
    assert debrief.strengths == ["Clear structure"]

    result = await delete_candidate_account_job(ctx, deletion_id, cid)
    assert result["status"] == "completed"
    async with pg_engine.connect() as c:
        left = {
            t: (await c.execute(text(f"SELECT count(*) FROM {t}"))).scalar()
            for t in ("candidates", "jobs", "practice_sessions", "session_debriefs", "job_blueprints", "job_requirements")
        }
        dj = (await c.execute(text("SELECT status, rows_deleted_summary FROM deletion_jobs WHERE id = CAST(:d AS uuid)"), {"d": deletion_id})).first()
    assert all(v == 0 for v in left.values()), left
    assert dj.status == "completed"
    summary = dj.rows_deleted_summary if isinstance(dj.rows_deleted_summary, dict) else json.loads(dj.rows_deleted_summary)
    assert summary["candidates"] == 1 and summary["jobs"] == 1 and summary["practice_sessions"] == 1
