import logging
from uuid import UUID
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_document(ctx: Dict[str, Any], document_id: UUID, file_url: str, candidate_id: UUID):
    """
    1. Download file from storage
    2. Extract text (PDF/DOCX)
    3. Validate (virus scan if available)
    4. Store in document_chunks table
    5. Enqueue embeddings job
    6. Update document status
    """
    logger.info(f"Processing document {document_id}")
    # Enqueue next stage
    redis = ctx.get('redis')
    if redis:
        await redis.enqueue_job('generate_embeddings', document_id)
