"""Backwards-compatible entry point; the real pipeline lives in worker_tasks.process_resume."""
from typing import Any, Dict

from backend.app.worker_tasks import process_resume


async def process_document(ctx: Dict[str, Any], document_id, *args, trace_carrier: dict = None, **kwargs):
    """Parse -> chunk -> embed -> store -> extract for one document (delegates to process_resume)."""
    return await process_resume(ctx, str(document_id), trace_carrier=trace_carrier)
