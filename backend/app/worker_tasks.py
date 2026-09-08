import logging
import json
from sqlalchemy import text
from typing import Dict, Any

logger = logging.getLogger(__name__)

import uuid
import asyncio
from opentelemetry import trace
from opentelemetry.propagate import extract

tracer = trace.get_tracer(__name__)

async def process_resume(ctx: Dict[str, Any], document_id: str, trace_carrier: dict = None):
    """
    STAGE 3 TODO: Replace this minimal extraction prompt with the full structured extraction spec.
    """
    otel_ctx = extract(trace_carrier or {})
    with tracer.start_as_current_span("process_resume", context=otel_ctx) as span:
        span.set_attribute("document_id", document_id)
        await _process_resume_inner(ctx, document_id)

async def _process_resume_inner(ctx: Dict[str, Any], document_id: str):
    db = ctx['db_engine']
    redis = ctx.get('redis') # using get for tests
    
    from backend.storage.local import get_object_storage
    from praxis_ai_gateway.router import GatewayRouter, RoutingContext
    from praxis_ai_gateway.registry import ModelRegistry
    from praxis_ai_gateway.base import LLMMessage
    from pydantic import BaseModel
    import pdfplumber
    import io

    # Update status to parsing
    async with db.begin() as conn:
        await conn.execute(text("UPDATE documents SET processing_status = 'parsing' WHERE id = :id"), {"id": document_id})
        doc_row = await conn.execute(text("SELECT storage_path, candidate_id FROM documents WHERE id = :id"), {"id": document_id})
        doc = doc_row.first()
        
    if not doc:
        return
        
    storage = get_object_storage()
    try:
        raw_bytes = await storage.get(doc.storage_path)
    except Exception as e:
        async with db.begin() as conn:
            await conn.execute(text("UPDATE documents SET processing_status = 'failed', error_message = :err WHERE id = :id"), {"id": document_id, "err": f"Storage error: {e}"})
        return

    # Extract text
    raw_text = ""
    try:
        if doc.storage_path.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                raw_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        else:
            raw_text = raw_bytes.decode('utf-8', errors='ignore') # Fallback
    except Exception as e:
        async with db.begin() as conn:
            await conn.execute(text("UPDATE documents SET processing_status = 'failed', error_message = :err WHERE id = :id"), {"id": document_id, "err": f"Parsing error: {e}"})
        return

    # Update status to embedding
    async with db.begin() as conn:
        await conn.execute(text("UPDATE documents SET processing_status = 'embedding' WHERE id = :id"), {"id": document_id})

    # Chunking: ~300 tokens (approx 1200 chars)
    chunks = [raw_text[i:i+1200] for i in range(0, len(raw_text), 1200) if raw_text[i:i+1200].strip()]

    # Setup Gateway
    providers = ctx.get('providers', {})
    router = GatewayRouter(ModelRegistry(), providers, redis, db)
    route_ctx = RoutingContext(user_id=str(doc.candidate_id))

    # Embed chunks
    try:
        embed_resp = await router.route("embedding", route_ctx, "embed", chunks)
        embeddings = embed_resp.result
        
        async with db.begin() as conn:
            for i, chunk_text in enumerate(chunks):
                if i < len(embeddings):
                    await conn.execute(text("""
                        INSERT INTO document_chunks (document_id, chunk_index, content, embedding_model, embedding_version)
                        VALUES (:doc_id, :idx, :content, :model, :version)
                    """), {
                        "doc_id": document_id, "idx": i, "content": chunk_text,
                        "model": embed_resp.model, "version": "v1"
                    })
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        # Non-fatal if we just want to proceed, but let's log it.

    # Gateway extraction (Reasoning alias)
    # STAGE 3 TODO: Replace this minimal extraction prompt with the full structured extraction spec.
    class ExtractedResume(BaseModel):
        skills: list[str]
        projects: list[str]

    messages = [
        LLMMessage(role="system", content="Extract candidate skills and projects from the resume."),
        LLMMessage(role="user", content=raw_text)
    ]
    
    try:
        extract_resp = await router.route("reasoning", route_ctx, "structured", messages, schema=ExtractedResume)
        parsed: ExtractedResume = extract_resp.result
        
        async with db.begin() as conn:
            # Minimal insertion to satisfy Stage 4 UI
            for proj in parsed.projects:
                await conn.execute(text("""
                    INSERT INTO candidate_projects (candidate_id, title, role, summary)
                    VALUES (:cid, :title, 'Unknown', :summary)
                """), {"cid": doc.candidate_id, "title": proj[:100], "summary": proj})
                
            for skill in parsed.skills:
                await conn.execute(text("""
                    INSERT INTO candidate_skills (candidate_id, name, proficiency)
                    VALUES (:cid, :name, 'Intermediate')
                """), {"cid": doc.candidate_id, "name": skill[:50]})
                
    except Exception as e:
        logger.error(f"Extraction failed: {e}")

    # Mark Ready
    async with db.begin() as conn:
        await conn.execute(text("UPDATE documents SET processing_status = 'ready' WHERE id = :id"), {"id": document_id})

async def analyze_job(ctx: Dict[str, Any], job_id: str, trace_carrier: dict = None):
    """
    STAGE 3 TODO: Replace this minimal extraction prompt with the full structured extraction spec.
    """
    otel_ctx = extract(trace_carrier or {})
    with tracer.start_as_current_span("analyze_job", context=otel_ctx) as span:
        span.set_attribute("job_id", job_id)
        await _analyze_job_inner(ctx, job_id)

async def _analyze_job_inner(ctx: Dict[str, Any], job_id: str):
    db = ctx['db_engine']
    redis = ctx.get('redis')
    
    from praxis_ai_gateway.router import GatewayRouter, RoutingContext
    from praxis_ai_gateway.registry import ModelRegistry
    from praxis_ai_gateway.base import LLMMessage
    from pydantic import BaseModel

    async with db.begin() as conn:
        await conn.execute(text("UPDATE jobs SET processing_status = 'parsing' WHERE id = :id"), {"id": job_id})
        job_row = await conn.execute(text("SELECT description, created_by FROM jobs WHERE id = :id"), {"id": job_id})
        job = job_row.first()
        
    if not job:
        return
        
    providers = ctx.get('providers', {})
    router = GatewayRouter(ModelRegistry(), providers, redis, db)
    route_ctx = RoutingContext(user_id=str(job.created_by))

    class ExtractedJob(BaseModel):
        requirements: list[str]
        blueprints: list[str]

    messages = [
        LLMMessage(role="system", content="Extract minimal requirements and interview blueprints from the job description."),
        LLMMessage(role="user", content=job.description or "")
    ]
    
    try:
        resp = await router.route("reasoning", route_ctx, "structured", messages, schema=ExtractedJob)
        parsed: ExtractedJob = resp.result
        
        async with db.begin() as conn:
            for req in parsed.requirements:
                await conn.execute(text("""
                    INSERT INTO job_requirements (job_id, category, description, importance)
                    VALUES (:jid, 'skill', :desc, 'required')
                """), {"jid": job_id, "desc": req})
                
            for bp in parsed.blueprints:
                await conn.execute(text("""
                    INSERT INTO job_blueprints (job_id, dimension, target_signal, scoring_rubric, created_by)
                    VALUES (:jid, 'technical', :sig, '{"pass": "good", "fail": "bad"}', :cid)
                """), {"jid": job_id, "sig": bp, "cid": job.created_by})
                
        async with db.begin() as conn:
            await conn.execute(text("UPDATE jobs SET processing_status = 'ready' WHERE id = :id"), {"id": job_id})
            
    except Exception as e:
        logger.error(f"Job analysis failed: {e}")
        async with db.begin() as conn:
            await conn.execute(text("UPDATE jobs SET processing_status = 'failed', error_message = :err WHERE id = :id"), {"id": job_id, "err": str(e)})

async def cleanup_old_sessions(ctx: Dict[str, Any]):
    db = ctx['db_engine']
    async with db.begin() as conn:
        query = text("""
            UPDATE practice_sessions
            SET status = 'abandoned', ended_at = NOW()
            WHERE status = 'active'
              AND id IN (
                  SELECT session_id 
                  FROM session_state_log 
                  GROUP BY session_id 
                  HAVING MAX(occurred_at) < NOW() - INTERVAL '2 hours'
              )
        """)
        await conn.execute(query)

async def purge_expired_retention_data(ctx: Dict[str, Any]):
    db = ctx['db_engine']
    from backend.storage.local import get_object_storage
    storage = get_object_storage()
    
    async with db.begin() as conn:
        # 1. Transcript segments
        query_transcripts = text("""
            WITH expired AS (
                SELECT ts.id, ts.session_id, ps.candidate_id
                FROM transcript_segments ts
                JOIN practice_sessions ps ON ts.session_id = ps.id
                JOIN user_settings us ON ps.candidate_id = us.profile_id
                WHERE ts.created_at < NOW() - (us.data_retention_days || ' days')::interval
            ),
            deleted AS (
                DELETE FROM transcript_segments
                WHERE id IN (SELECT id FROM expired)
                RETURNING id, candidate_id
            )
            INSERT INTO privacy_events (candidate_id, action, entity_type, details)
            SELECT candidate_id, 'retention_purge', 'transcript_segments', 'Purged ' || count(*) || ' expired segments'
            FROM deleted
            GROUP BY candidate_id;
        """)
        await conn.execute(query_transcripts)
        
        # 2. Documents/Chunks
        query_docs = text("""
            WITH expired AS (
                SELECT d.id, d.storage_path, d.candidate_id
                FROM documents d
                JOIN user_settings us ON d.candidate_id = us.profile_id
                WHERE d.created_at < NOW() - (us.data_retention_days || ' days')::interval
            ),
            deleted AS (
                DELETE FROM documents
                WHERE id IN (SELECT id FROM expired)
                RETURNING id, storage_path, candidate_id
            )
            SELECT storage_path, candidate_id FROM deleted;
        """)
        res = await conn.execute(query_docs)
        deleted_docs = res.fetchall()
        
        for doc in deleted_docs:
            try:
                await storage.delete(doc.storage_path)
            except Exception as e:
                logger.error(f"Failed to delete {doc.storage_path}: {e}")
                
            await conn.execute(text("""
                INSERT INTO privacy_events (candidate_id, action, entity_type, details)
                VALUES (:cid, 'retention_purge', 'documents', 'Purged expired document ' || :path)
            """), {"cid": doc.candidate_id, "path": doc.storage_path})
