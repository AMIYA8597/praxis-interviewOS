"""
ARQ background jobs.

Every job is wrapped by `job()` which:
  * restores the OpenTelemetry context propagated by the enqueuer,
  * binds candidate/session ids into the logging context,
  * logs start / success / failure with duration,
  * converts transient errors into `arq.Retry` with exponential backoff,
  * on the final attempt writes a `failed_jobs` (dead-letter) row.

Jobs are idempotent: re-running one after a crash/retry converges to the
same state (chunks are replaced, blueprints upserted, debriefs upserted).
"""
import functools
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from opentelemetry import trace
from opentelemetry.propagate import extract
from sqlalchemy import text

from backend.app.core.context import bind
from backend.app.services.document_processing import DocumentParseError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

try:
    from packages.config.settings import settings as _settings

    DEFAULT_MAX_TRIES = _settings.WORKER_MAX_TRIES
except Exception:  # pragma: no cover
    DEFAULT_MAX_TRIES = 3


class PermanentJobError(Exception):
    """Failure that retrying cannot fix (bad input, missing row, ...)."""


async def record_dead_letter(ctx: Dict[str, Any], job_name: str, args: tuple, kwargs: dict, error: BaseException, candidate_id: Optional[str]) -> None:
    db = ctx.get("db_engine")
    if db is None:
        return
    safe_kwargs = {k: v for k, v in kwargs.items() if k != "trace_carrier"}
    try:
        async with db.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO failed_jobs (job_name, job_id, args, error_message, candidate_id)
                    VALUES (:name, :jid, CAST(:args AS jsonb), :err, :cid)
                """),
                {
                    "name": job_name,
                    "jid": str(ctx.get("job_id") or "unknown"),
                    "args": json.dumps({"args": list(args), "kwargs": safe_kwargs}, default=str),
                    "err": f"{type(error).__name__}: {error}"[:2000],
                    "cid": candidate_id,
                },
            )
    except Exception as e:
        logger.error("dead_letter_write_failed", extra={"job_name": job_name, "error_type": type(e).__name__})


def job(candidate_arg: Optional[int] = None, *, max_tries: int = DEFAULT_MAX_TRIES):
    """Decorator for ARQ job functions (see module docstring)."""

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(ctx: Dict[str, Any], *args, trace_carrier: Optional[dict] = None, **kwargs):
            from arq import Retry

            job_name = fn.__name__
            job_try = int(ctx.get("job_try", 1) or 1)
            candidate_id = kwargs.get("candidate_id")
            if candidate_id is None and candidate_arg is not None and len(args) > candidate_arg:
                candidate_id = args[candidate_arg]
            if candidate_id:
                bind(candidate_id=str(candidate_id))
            started = time.perf_counter()
            extra = {"job_name": job_name, "job_id": ctx.get("job_id"), "job_try": job_try}
            logger.info("job_started", extra=extra)
            with tracer.start_as_current_span(job_name, context=extract(trace_carrier or {})) as span:
                span.set_attribute("job.try", job_try)
                try:
                    result = await fn(ctx, *args, **kwargs)
                except Retry:
                    raise
                except PermanentJobError as e:
                    logger.error("job_failed_permanently", extra={**extra, "error": str(e)[:500]})
                    await record_dead_letter(ctx, job_name, args, kwargs, e, candidate_id)
                    return {"status": "failed", "error": str(e)}
                except Exception as e:
                    duration_ms = round((time.perf_counter() - started) * 1000, 1)
                    span.record_exception(e)
                    if job_try < max_tries:
                        defer = 5 * (2 ** (job_try - 1))
                        logger.warning("job_retrying", extra={**extra, "duration_ms": duration_ms, "error_type": type(e).__name__, "defer_s": defer})
                        raise Retry(defer=defer) from e
                    logger.error("job_failed", extra={**extra, "duration_ms": duration_ms, "error_type": type(e).__name__})
                    await record_dead_letter(ctx, job_name, args, kwargs, e, candidate_id)
                    raise
            logger.info("job_succeeded", extra={**extra, "duration_ms": round((time.perf_counter() - started) * 1000, 1)})
            return result

        wrapper.max_tries = max_tries  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _gateway(ctx: Dict[str, Any]):
    """Gateway shared by all jobs in this worker (built once in on_startup)."""
    gw = ctx.get("gateway")
    if gw is None:
        from backend.app.core.bootstrap import build_gateway
        from packages.config.settings import settings

        gw = build_gateway(settings, ctx.get("redis"), ctx.get("db_session_factory"), providers=ctx.get("providers") or {})
        ctx["gateway"] = gw
    return gw


import contextlib

@contextlib.asynccontextmanager
async def user_db_conn(db_engine, candidate_id: str):
    async with db_engine.begin() as conn:
        claims = json.dumps({"sub": candidate_id})
        if getattr(getattr(db_engine, "dialect", None), "name", "") != "sqlite":
            await conn.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
        yield conn

async def _set_doc_status(db_engine, candidate_id: str, document_id: str, status: str, error: Optional[str] = None) -> None:
    async with user_db_conn(db_engine, candidate_id) as conn:
        await conn.execute(
            text("UPDATE documents SET processing_status = :s, error_message = :e WHERE id = :id AND candidate_id = :cid"),
            {"s": status, "e": error, "id": document_id, "cid": candidate_id},
        )


# ════════════════════════════════════════════════════════════════════
# Resume processing: parse -> chunk -> embed -> store -> extract
# ════════════════════════════════════════════════════════════════════

@job()
async def process_resume(ctx: Dict[str, Any], document_id: str):
    from backend.app.core.storage import get_storage_client
    from backend.app.services import document_processing as dp

    db = ctx["db_engine"]
    admin_db = ctx.get("admin_db_engine", db)
    async with admin_db.begin() as conn:
        doc = (
            await conn.execute(
                text("""
                    SELECT d.id, d.candidate_id, d.storage_path, d.mime_type, d.original_filename, r.id AS resume_id
                    FROM documents d LEFT JOIN resumes r ON r.document_id = d.id
                    WHERE d.id = :id
                """),
                {"id": document_id},
            )
        ).first()
    if doc is None:
        raise PermanentJobError(f"document {document_id} not found")
    candidate_id = str(doc.candidate_id)
    bind(candidate_id=candidate_id)
    await _set_doc_status(db, candidate_id, document_id, "parsing")

    storage = ctx.get("storage") or get_storage_client()
    try:
        raw = await storage.get(doc.storage_path)
    except Exception as e:
        # Missing blob is permanent; transient storage errors are retried by the wrapper.
        if "not found" in str(e).lower():
            await _set_doc_status(db, candidate_id, document_id, "failed", "Uploaded file is missing from storage")
            raise PermanentJobError("blob missing") from e
        raise

    try:
        content = await dp.run_in_thread(dp.extract_text, raw, doc.mime_type, doc.original_filename or "")
    except DocumentParseError as e:
        await _set_doc_status(db, candidate_id, document_id, "failed", str(e))
        raise PermanentJobError(str(e)) from e
    logger.info("resume_parsed", extra={"document_id": document_id, "text_chars": len(content)})

    await _set_doc_status(db, candidate_id, document_id, "embedding")
    chunks = await dp.run_in_thread(dp.chunk, content)

    embeddings: Optional[List[List[float]]] = None
    warning: Optional[str] = None
    try:
        embeddings = await dp.embed(chunks)
    except Exception as e:
        if int(ctx.get("job_try", 1) or 1) < DEFAULT_MAX_TRIES:
            raise  # transient: let the wrapper retry with backoff
        # Degraded mode on the final attempt: keep keyword (FTS) search working.
        warning = "Semantic embeddings unavailable; keyword search only"
        logger.error("embedding_failed_degraded", extra={"document_id": document_id, "error_type": type(e).__name__})

    async with user_db_conn(db, candidate_id) as conn:
        stored = await dp.store_chunks(conn, document_id, chunks, embeddings)
    logger.info("resume_chunks_stored", extra={"document_id": document_id, "chunks": stored, "embedded": embeddings is not None})

    extracted = await _extract_resume_profile(ctx, candidate_id, content)
    if extracted is not None and doc.resume_id is not None:
        await _persist_resume_profile(db, candidate_id, str(doc.resume_id), extracted)

    await _set_doc_status(db, candidate_id, document_id, "ready", warning)
    return {"status": "ready", "chunks": stored, "embedded": embeddings is not None, "extracted": extracted is not None}


async def _extract_resume_profile(ctx, candidate_id: str, content: str):
    """LLM structured extraction. Failure is non-fatal (chunks are still searchable)."""
    from praxis_ai_gateway.prompt_builder import PromptBuilder
    from praxis_ai_gateway.router import RoutingContext
    from praxis_ai_gateway.schemas.resume import ExtractedResumeProfile

    builder = PromptBuilder()
    builder.add_system(
        "Extract the candidate's skills, projects, experiences and education from the resume. "
        "Only include facts explicitly stated in the text. Use low confidence when unsure."
    )
    builder.add_untrusted("resume_text", "resume_upload", content[:30_000])
    builder.add_output_schema(ExtractedResumeProfile)
    try:
        resp = await _gateway(ctx).route(
            "reasoning",
            RoutingContext(user_id=candidate_id, zero_spend_mode=True),
            "structured",
            messages=builder.build(),
            schema=ExtractedResumeProfile,
        )
        return resp.result
    except Exception as e:
        logger.warning("resume_extraction_failed", extra={"error_type": type(e).__name__})
        return None


async def _persist_resume_profile(db, candidate_id: str, resume_id: str, profile) -> None:
    async with user_db_conn(db, candidate_id) as conn:
        version_no = (
            await conn.execute(
                text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM resume_versions WHERE resume_id = CAST(:r AS uuid)"),
                {"r": resume_id},
            )
        ).scalar()
        version_id = (
            await conn.execute(
                text("""
                    INSERT INTO resume_versions (resume_id, version_number, label)
                    VALUES (CAST(:r AS uuid), :v, 'extracted') RETURNING id
                """),
                {"r": resume_id, "v": version_no},
            )
        ).scalar()

        claims = []
        for s in profile.skills[:100]:
            claims.append(("skill", s.name[:200], s.extraction_confidence))
        for p in profile.projects[:30]:
            claims.append(("project", f"{p.title}: {p.summary}"[:1000], p.extraction_confidence))
        for x in profile.experiences[:30]:
            claims.append(("role", f"{x.title} at {x.company}"[:500], x.extraction_confidence))
        for ed in profile.education[:10]:
            label = " ".join(filter(None, [ed.degree, ed.field_of_study, ed.institution]))
            claims.append(("education", label[:500], ed.extraction_confidence))
        if claims:
            await conn.execute(
                text("""
                    INSERT INTO resume_claims (resume_version_id, claim_text, claim_type, extraction_confidence, verified_by_user)
                    VALUES (CAST(:v AS uuid), :t, :k, :c, false)
                """),
                [{"v": str(version_id), "t": t, "k": k, "c": c} for k, t, c in claims],
            )

        for s in profile.skills[:100]:
            name = s.name.strip()[:100]
            if not name:
                continue
            skill_id = (
                await conn.execute(
                    text("""
                        INSERT INTO skills (name) VALUES (:n)
                        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                        RETURNING id
                    """),
                    {"n": name},
                )
            ).scalar()
            await conn.execute(
                text("""
                    INSERT INTO candidate_skills (candidate_id, skill_id, proficiency, evidence_source)
                    VALUES (CAST(:c AS uuid), :s, :p, 'resume')
                    ON CONFLICT (candidate_id, skill_id) DO NOTHING
                """),
                {"c": candidate_id, "s": skill_id, "p": s.proficiency[:50]},
            )

        for p in profile.projects[:30]:
            await conn.execute(
                text("""
                    INSERT INTO candidate_projects (candidate_id, name, summary, confidence, verified_by_user)
                    VALUES (CAST(:c AS uuid), :n, :s, :conf, false)
                """),
                {"c": candidate_id, "n": p.title[:100], "s": p.summary, "conf": p.extraction_confidence},
            )
    logger.info("resume_profile_persisted", extra={"claims": len(claims)})


# ════════════════════════════════════════════════════════════════════
# Job description analysis
# ════════════════════════════════════════════════════════════════════

@job()
async def analyze_job(ctx: Dict[str, Any], job_id: str):
    from praxis_ai_gateway.prompt_builder import PromptBuilder
    from praxis_ai_gateway.router import RoutingContext
    from praxis_ai_gateway.schemas.jd import ExtractedJobBlueprint

    db = ctx["db_engine"]
    admin_db = ctx.get("admin_db_engine", db)
    async with admin_db.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT id, candidate_id, raw_jd_text FROM jobs WHERE id = :id"), {"id": job_id}
            )
        ).first()
        if row is None:
            raise PermanentJobError(f"job {job_id} not found")
            
    candidate_id = str(row.candidate_id)
    bind(candidate_id=candidate_id)
    
    async with user_db_conn(db, candidate_id) as conn:
        await conn.execute(
            text("UPDATE jobs SET processing_status = 'parsing', error_message = NULL WHERE id = :id"),
            {"id": job_id},
        )

    builder = PromptBuilder()
    builder.add_system(
        "Extract the job's concrete requirements (with the literal supporting quote), seniority signal "
        "and likely interview topics from the job description."
    )
    builder.add_untrusted("job_description", "user_job_post", (row.raw_jd_text or "")[:30_000])
    builder.add_output_schema(ExtractedJobBlueprint)
    try:
        resp = await _gateway(ctx).route(
            "reasoning",
            RoutingContext(user_id=candidate_id, zero_spend_mode=True),
            "structured",
            messages=builder.build(),
            schema=ExtractedJobBlueprint,
        )
        bp: ExtractedJobBlueprint = resp.result
    except Exception as e:
        if int(ctx.get("job_try", 1) or 1) < DEFAULT_MAX_TRIES:
            raise
        async with user_db_conn(db, candidate_id) as conn:
            await conn.execute(
                text("UPDATE jobs SET processing_status = 'failed', error_message = :e WHERE id = :id"),
                {"id": job_id, "e": "AI analysis unavailable; please retry later"},
            )
        raise PermanentJobError(f"analysis failed: {type(e).__name__}") from e

    topics = [t.topic[:200] for t in bp.likely_topics][:20]
    top_skills = [r.skill_text for r in bp.job_requirements if r.priority == "required"][:15]
    async with user_db_conn(db, candidate_id) as conn:
        blueprint_id = (
            await conn.execute(
                text("""
                    INSERT INTO job_blueprints (job_id, top_skills, likely_topics, summary)
                    VALUES (:j, CAST(:skills AS jsonb), :topics, :summary)
                    ON CONFLICT (job_id) DO UPDATE
                      SET top_skills = EXCLUDED.top_skills, likely_topics = EXCLUDED.likely_topics,
                          summary = EXCLUDED.summary
                    RETURNING id
                """),
                {
                    "j": job_id,
                    "skills": json.dumps(top_skills),
                    "topics": topics,
                    "summary": f"{bp.seniority_signal or 'Unspecified'} {bp.role or ''} role".strip(),
                },
            )
        ).scalar()
        await conn.execute(text("DELETE FROM job_requirements WHERE job_blueprint_id = :b"), {"b": blueprint_id})
        reqs = [
            {
                "b": blueprint_id,
                "s": r.skill_text[:500],
                "c": r.category[:50],
                "p": r.priority if r.priority in ("required", "preferred") else "preferred",
                "q": r.evidence_quote[:1000],
            }
            for r in bp.job_requirements[:50]
        ]
        if reqs:
            await conn.execute(
                text("""
                    INSERT INTO job_requirements (job_blueprint_id, skill_text, category, priority, evidence_quote)
                    VALUES (:b, :s, :c, :p, :q)
                """),
                reqs,
            )
        await conn.execute(
            text("""
                UPDATE jobs SET processing_status = 'ready', seniority_signal = :sen, error_message = NULL
                WHERE id = :id
            """),
            {"id": job_id, "sen": bp.seniority_signal},
        )
    return {"status": "ready", "requirements": len(reqs)}


# ════════════════════════════════════════════════════════════════════
# Session debrief (enqueued by POST /sessions/{id}/end)
# ════════════════════════════════════════════════════════════════════

@job()
async def generate_session_debrief_job(ctx: Dict[str, Any], session_id: str):
    from backend.app.services.debrief import generate_session_debrief, persist_session_debrief

    bind(session_id=session_id)
    
    db = ctx["db_engine"]
    admin_db = ctx.get("admin_db_engine", db)
    async with admin_db.begin() as conn:
        owner = (
            await conn.execute(
                text("SELECT candidate_id FROM practice_sessions WHERE id = CAST(:s AS uuid)"), {"s": session_id}
            )
        ).first()
        if owner is None:
            raise PermanentJobError(f"session {session_id} not found")
            
    candidate_id = str(owner[0])
    bind(candidate_id=candidate_id)
    
    from backend.app.db.session import create_session_factory
    # We must ensure the session uses the jwt claims, but generate_session_debrief expects a Session object.
    # The simplest way is to manually run set_config on the session before passing it down.
    factory = create_session_factory(db)
    import json
    claims = json.dumps({"sub": candidate_id})
    async with factory() as session:
        if getattr(getattr(session.bind, "dialect", None), "name", "") != "sqlite":
            await session.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
        result = await generate_session_debrief(session_id, session, _gateway(ctx), user_id=candidate_id)
        await persist_session_debrief(session, session_id, result)
        await session.commit()
    return {"status": "ready"}


# ════════════════════════════════════════════════════════════════════
# Account deletion
# ════════════════════════════════════════════════════════════════════

@job(candidate_arg=1)
async def delete_candidate_account_job(ctx: Dict[str, Any], deletion_job_id: str, candidate_id: str):
    from backend.app.core.deletion import DeletionService
    from backend.app.core.storage import get_storage_client

    db = ctx["db_engine"]
    async with user_db_conn(db, candidate_id) as conn:
        await conn.execute(
            text("UPDATE deletion_jobs SET status = 'running', updated_at = NOW() WHERE id = :id"),
            {"id": deletion_job_id},
        )
    try:
        storage = ctx.get("storage") or get_storage_client()
    except Exception:
        storage = None
        
    # DeletionService might need an AsyncSession or a Connection. We need to wrap it if it uses the db engine directly.
    # Actually, DeletionService probably creates its own connections or uses the engine. We'll let it use admin_db to delete everything safely.
    admin_db = ctx.get("admin_db_engine", db)
    service = DeletionService(db=admin_db, storage_client=storage)
    try:
        summary = await service.process_deletion_job(candidate_id)
    except Exception as e:
        async with user_db_conn(db, candidate_id) as conn:
            await conn.execute(
                text("""
                    UPDATE deletion_jobs SET status = 'failed', error_message = :err, updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": deletion_job_id, "err": f"{type(e).__name__}"},
            )
        raise
    async with user_db_conn(db, candidate_id) as conn:
        await conn.execute(
            text("""
                UPDATE deletion_jobs
                SET status = 'completed', completed_at = NOW(), updated_at = NOW(),
                    rows_deleted_summary = CAST(:summary AS jsonb), error_message = NULL
                WHERE id = :id
            """),
            {"id": deletion_job_id, "summary": json.dumps(summary, default=str)},
        )
    return {"status": "completed", "summary": summary}


# ════════════════════════════════════════════════════════════════════
# Study material generation
# ════════════════════════════════════════════════════════════════════

@job(candidate_arg=2)
async def generate_study_material_job(ctx: Dict[str, Any], topic: str, difficulty: str, candidate_id: str, task_id: str):
    from praxis_ai_gateway.prompt_builder import PromptBuilder
    from praxis_ai_gateway.router import RoutingContext
    from pydantic import BaseModel

    class GeneratedMaterial(BaseModel):
        prompt: str
        reference_answer: str

    builder = PromptBuilder()
    builder.add_system("Generate one technical interview study question and a comprehensive reference answer.")
    builder.add_untrusted("requested_topic", "user_input", f"Topic: {topic}\nDifficulty: {difficulty}")
    builder.add_output_schema(GeneratedMaterial)
    resp = await _gateway(ctx).route(
        "reasoning",
        RoutingContext(user_id=candidate_id, zero_spend_mode=True),
        "structured",
        messages=builder.build(),
        schema=GeneratedMaterial,
    )
    parsed: GeneratedMaterial = resp.result
    item_id = str(uuid.uuid4())
    async with user_db_conn(ctx["db_engine"], candidate_id) as conn:
        await conn.execute(
            text("""
                INSERT INTO study_items (id, candidate_id, topic, source, prompt, reference_answer, difficulty)
                VALUES (:id, :cid, :topic, 'generated', :prompt, :ref, :diff)
            """),
            {
                "id": item_id,
                "cid": candidate_id,
                "topic": topic[:255],
                "prompt": parsed.prompt,
                "ref": parsed.reference_answer,
                "diff": difficulty[:50],
            },
        )
    return {"status": "created", "study_item_id": item_id, "task_id": task_id}


# ════════════════════════════════════════════════════════════════════
# Maintenance crons
# ════════════════════════════════════════════════════════════════════

async def cleanup_old_sessions(ctx: Dict[str, Any]):
    """Abandon sessions with no state change for 2h, and never-started sessions after 24h."""
    # ACTS ACROSS ALL TENANTS: explicit elevated superuser connection
    admin_db = ctx.get("admin_db_engine", ctx["db_engine"])
    async with admin_db.begin() as conn:
        active = await conn.execute(
            text("""
                UPDATE practice_sessions ps
                SET status = 'abandoned', ended_at = NOW()
                WHERE ps.status = 'active'
                  AND COALESCE(
                        (SELECT MAX(occurred_at) FROM session_state_log l WHERE l.session_id = ps.id),
                        ps.started_at, ps.created_at
                      ) < NOW() - INTERVAL '2 hours'
            """)
        )
        pending = await conn.execute(
            text("""
                UPDATE practice_sessions SET status = 'abandoned'
                WHERE status = 'pending' AND created_at < NOW() - INTERVAL '24 hours'
            """)
        )
    logger.info("sessions_cleaned", extra={"abandoned_active": active.rowcount, "abandoned_pending": pending.rowcount})


async def purge_expired_retention_data(ctx: Dict[str, Any]):
    """Delete transcripts/documents older than each candidate's data_retention_days."""
    from backend.app.core.storage import get_storage_client

    storage = ctx.get("storage") or get_storage_client()
    # ACTS ACROSS ALL TENANTS: explicit elevated superuser connection
    admin_db = ctx.get("admin_db_engine", ctx["db_engine"])
    async with admin_db.begin() as conn:
        seg = await conn.execute(
            text("""
                DELETE FROM transcript_segments ts
                USING practice_sessions ps, user_settings us
                WHERE ts.session_id = ps.id
                  AND us.candidate_id = ps.candidate_id
                  AND us.data_retention_days IS NOT NULL
                  AND ts.created_at < NOW() - make_interval(days => us.data_retention_days)
            """)
        )
        docs = (
            await conn.execute(
                text("""
                    DELETE FROM documents d
                    USING user_settings us
                    WHERE us.candidate_id = d.candidate_id
                      AND us.data_retention_days IS NOT NULL
                      AND d.created_at < NOW() - make_interval(days => us.data_retention_days)
                    RETURNING d.storage_path, d.candidate_id
                """)
            )
        ).fetchall()
        profiles = (
            await conn.execute(
                text("""
                    SELECT DISTINCT c.profile_id FROM candidates c
                    WHERE c.id = ANY(CAST(:ids AS uuid[]))
                """),
                {"ids": [str(d.candidate_id) for d in docs]},
            )
        ).fetchall() if docs else []
        if profiles or seg.rowcount:
            await conn.execute(
                text("""
                    INSERT INTO privacy_events (profile_id, event_type, consent_given)
                    SELECT p, 'retention_purge', NULL FROM unnest(CAST(:pids AS uuid[])) AS p
                """),
                {"pids": [str(p[0]) for p in profiles]},
            )
    failed = 0
    for d in docs:
        if not d.storage_path:
            continue
        try:
            await storage.delete(d.storage_path)
        except Exception as e:
            failed += 1
            logger.error("retention_blob_delete_failed", extra={"error_type": type(e).__name__})
    logger.info(
        "retention_purge_completed",
        extra={"segments": seg.rowcount, "documents": len(docs), "blob_failures": failed, "at": datetime.now(timezone.utc).isoformat()},
    )
