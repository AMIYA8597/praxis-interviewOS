"""
Resume/document processing primitives used by the ARQ worker:

    extract_text -> chunk -> embed -> store_chunks

All functions are pure/async and independent of ARQ so they can be unit
tested. Nothing here logs document content (only lengths/counts).
"""
import asyncio
import io
import logging
import re
import zipfile
from typing import List, Optional, Sequence
from xml.etree import ElementTree

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT = "text/plain"

MAX_TEXT_CHARS = 200_000  # hard cap so a pathological file can't blow up memory/LLM cost
_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentParseError(Exception):
    """Permanent failure: retrying will not help."""


def _extract_pdf(data: bytes) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        pass
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        info = zf.getinfo("word/document.xml")
        if info.file_size > 50 * 1024 * 1024:  # zip-bomb guard
            raise DocumentParseError("DOCX body too large")
        xml = zf.read(info)
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for para in root.iter(f"{_W_NS}p"):
        parts = []
        for node in para.iter():
            if node.tag == f"{_W_NS}t":
                parts.append(node.text or "")
            elif node.tag in (f"{_W_NS}tab", f"{_W_NS}br"):
                parts.append(" ")
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


def extract_text(data: bytes, mime_type: Optional[str], filename: str = "") -> str:
    """Extract plain text; raises DocumentParseError on unreadable input."""
    mime = (mime_type or "").lower()
    name = filename.lower()
    try:
        if mime == PDF or name.endswith(".pdf"):
            raw = _extract_pdf(data)
        elif mime == DOCX or name.endswith(".docx"):
            raw = _extract_docx(data)
        elif mime == TXT or name.endswith(".txt"):
            raw = data.decode("utf-8", errors="replace")
        else:
            raise DocumentParseError(f"Unsupported document type: {mime or 'unknown'}")
    except DocumentParseError:
        raise
    except Exception as e:
        raise DocumentParseError(f"Could not read document ({type(e).__name__})") from e
    cleaned = re.sub(r"[ \t\x0b\x0c\r]+", " ", raw.replace("\x00", ""))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        raise DocumentParseError("No extractable text (scanned/image-only document?)")
    return cleaned[:MAX_TEXT_CHARS]


def chunk(text_value: str, target_tokens: int = 300, overlap_tokens: int = 50) -> List[str]:
    try:
        from praxis_ai_gateway.chunking import chunk_text

        chunks = chunk_text(text_value, target_tokens=target_tokens, overlap_tokens=overlap_tokens)
    except Exception as e:
        # tiktoken may be unavailable offline; fall back to ~4 chars/token windows.
        logger.warning("chunker_fallback", extra={"error_type": type(e).__name__})
        size, step = target_tokens * 4, (target_tokens - overlap_tokens) * 4
        chunks = [text_value[i : i + size] for i in range(0, len(text_value), step)]
    return [c for c in (c.strip() for c in chunks) if c]


async def embed(chunks: Sequence[str]) -> List[List[float]]:
    from praxis_ai_gateway.embeddings import embed_texts

    return await embed_texts(list(chunks), normalize=True, batch_size=32)


def embedding_model_info() -> tuple[str, str]:
    try:
        from praxis_ai_gateway.embeddings import EMBEDDING_MODEL_NAME, EMBEDDING_VERSION

        return EMBEDDING_MODEL_NAME, EMBEDDING_VERSION
    except Exception:
        return "BAAI/bge-small-en-v1.5", "v1"


async def _embedding_is_vector(conn: AsyncConnection) -> bool:
    row = (
        await conn.execute(
            text("""
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                WHERE a.attrelid = 'document_chunks'::regclass AND a.attname = 'embedding' AND NOT a.attisdropped
            """)
        )
    ).first()
    return bool(row and str(row[0]).startswith("vector"))


def _vector_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


async def store_chunks(
    conn: AsyncConnection,
    document_id: str,
    chunks: Sequence[str],
    embeddings: Optional[Sequence[Sequence[float]]],
    *,
    token_counts: Optional[Sequence[int]] = None,
) -> int:
    """Replace all chunks of a document (idempotent across job retries)."""
    model, version = embedding_model_info()
    await conn.execute(text("DELETE FROM document_chunks WHERE document_id = CAST(:d AS uuid)"), {"d": document_id})
    if not chunks:
        return 0
    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("embedding count does not match chunk count")
    emb_expr = "CAST(:emb AS vector)" if (embeddings is not None and await _embedding_is_vector(conn)) else ":emb"
    stmt = text(f"""
        INSERT INTO document_chunks (document_id, chunk_index, content, token_count, embedding,
                                     embedding_model, embedding_version, metadata)
        VALUES (CAST(:d AS uuid), :idx, :content, :tokens, {emb_expr}, :model, :version, CAST(:meta AS jsonb))
    """)
    rows = []
    for i, content in enumerate(chunks):
        rows.append(
            {
                "d": document_id,
                "idx": i,
                "content": content,
                "tokens": token_counts[i] if token_counts else None,
                "emb": _vector_literal(embeddings[i]) if embeddings is not None else None,
                "model": model if embeddings is not None else "none",
                "version": version if embeddings is not None else "none",
                "meta": '{"source": "resume"}',
            }
        )
    await conn.execute(stmt, rows)
    return len(rows)


async def run_in_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)
