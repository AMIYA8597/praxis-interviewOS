"""
Embedding backfill: (re-)embeds chunks of a document that have no
embedding yet, e.g. after process_resume ran in degraded keyword-only mode
or after an embedding-model upgrade.
"""
import logging
from typing import Any, Dict

from sqlalchemy import text

from backend.app.services import document_processing as dp
from backend.app.worker_tasks import job

logger = logging.getLogger(__name__)


@job()
async def generate_embeddings(ctx: Dict[str, Any], document_id, batch_size: int = 32):
    db = ctx["db_engine"]
    async with db.connect() as conn:
        rows = (
            await conn.execute(
                text("""
                    SELECT id, content FROM document_chunks
                    WHERE document_id = CAST(:d AS uuid) AND embedding IS NULL
                    ORDER BY chunk_index
                """),
                {"d": str(document_id)},
            )
        ).fetchall()
    if not rows:
        return {"status": "noop", "embedded": 0}

    model, version = dp.embedding_model_info()
    embedded = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        vectors = await dp.embed([r.content for r in batch])
        async with db.begin() as conn:
            emb_expr = "CAST(:emb AS vector)" if await dp._embedding_is_vector(conn) else ":emb"
            await conn.execute(
                text(f"""
                    UPDATE document_chunks
                    SET embedding = {emb_expr}, embedding_model = :model, embedding_version = :version
                    WHERE id = :id
                """),
                [
                    {"id": r.id, "emb": dp._vector_literal(v), "model": model, "version": version}
                    for r, v in zip(batch, vectors)
                ],
            )
        embedded += len(batch)
    async with db.begin() as conn:
        await conn.execute(
            text("""
                UPDATE documents SET error_message = NULL
                WHERE id = CAST(:d AS uuid) AND processing_status = 'ready'
            """),
            {"d": str(document_id)},
        )
    logger.info("embeddings_backfilled", extra={"document_id": str(document_id), "embedded": embedded})
    return {"status": "ready", "embedded": embedded}
