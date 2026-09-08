import io
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DocumentChunk
from app.rag.embeddings import embed_text

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    # Very basic word-level chunking for MVP
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap
    return chunks

async def process_and_store_document(db: AsyncSession, resume_id: str, raw_text: str):
    chunks = chunk_text(raw_text)
    
    for chunk in chunks:
        if not chunk.strip():
            continue
        vector = embed_text(chunk)
        doc_chunk = DocumentChunk(
            resume_id=resume_id,
            content=chunk,
            embedding=vector,
            metadata_={"source": "resume"}
        )
        db.add(doc_chunk)
    
    await db.commit()
