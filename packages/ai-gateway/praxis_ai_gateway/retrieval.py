import asyncio
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from praxis_ai_gateway.embeddings import embed_texts

class ScoredChunk(BaseModel):
    id: str
    document_id: str
    content: str
    score: float
    rank: Optional[int] = None
    original_filename: str = "unknown"
    chunk_index: int = 0

async def vector_search(query: str, candidate_id: str, db: AsyncEngine, k: int = 10, document_kind: Optional[str] = None, boost_verified: bool = False) -> List[ScoredChunk]:
    # embed the query
    embs = await embed_texts([query], normalize=True, batch_size=1)
    query_vector = embs[0]
    
    # query DB
    # We join documents to filter by candidate_id and document_kind
    # For boost_verified, if True, we only return chunks where metadata->>'verified_by_user' = 'true' 
    # OR we assume if there are unverified claims, we exclude. Let's do a strict filter on metadata.
    sql = """
        SELECT dc.id, dc.document_id, dc.content, dc.chunk_index, d.original_filename, 1 - (dc.embedding <=> :vec::vector) as similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.candidate_id = :candidate_id
    """
    params = {"vec": str(query_vector), "candidate_id": candidate_id}
    
    if document_kind:
        sql += " AND d.kind = :doc_kind"
        params["doc_kind"] = document_kind
        
    if boost_verified:
        # A hard filter: exclude chunks with unverified facts.
        # We check if the document has unverified claims, or we just rely on metadata.
        # Using EXISTS on resume_claims if it's a resume.
        sql += """
            AND NOT EXISTS (
                SELECT 1 FROM resume_claims rc
                JOIN resume_versions rv ON rv.id = rc.resume_version_id
                WHERE rv.document_id = d.id 
                  AND rc.verified_by_user = false
                  AND dc.content ILIKE '%' || rc.claim_text || '%'
            )
        """
        
    sql += " ORDER BY dc.embedding <=> :vec::vector LIMIT :k"
    params["k"] = k
    
    async with db.connect() as conn:
        result = await conn.execute(text(sql), params)
        rows = result.fetchall()
        
    return [ScoredChunk(id=str(row.id), document_id=str(row.document_id), content=row.content, score=row.similarity, original_filename=row.original_filename or "unknown", chunk_index=row.chunk_index) for row in rows]

async def fulltext_search(query: str, candidate_id: str, db: AsyncEngine, k: int = 10, document_kind: Optional[str] = None, boost_verified: bool = False) -> List[ScoredChunk]:
    sql = """
        SELECT dc.id, dc.document_id, dc.content, dc.chunk_index, d.original_filename, ts_rank(dc.content_tsv, plainto_tsquery('english', :query)) as rank_score
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.candidate_id = :candidate_id
          AND dc.content_tsv @@ plainto_tsquery('english', :query)
    """
    params = {"query": query, "candidate_id": candidate_id}
    
    if document_kind:
        sql += " AND d.kind = :doc_kind"
        params["doc_kind"] = document_kind
        
    if boost_verified:
        sql += """
            AND NOT EXISTS (
                SELECT 1 FROM resume_claims rc
                JOIN resume_versions rv ON rv.id = rc.resume_version_id
                WHERE rv.document_id = d.id 
                  AND rc.verified_by_user = false
                  AND dc.content ILIKE '%' || rc.claim_text || '%'
            )
        """
        
    sql += " ORDER BY rank_score DESC LIMIT :k"
    params["k"] = k
    
    async with db.connect() as conn:
        result = await conn.execute(text(sql), params)
        rows = result.fetchall()
        
    return [ScoredChunk(id=str(row.id), document_id=str(row.document_id), content=row.content, score=row.rank_score, original_filename=row.original_filename or "unknown", chunk_index=row.chunk_index) for row in rows]

async def hybrid_search(query: str, candidate_id: str, db: AsyncEngine, k: int = 8, document_kind: Optional[str] = None, boost_verified: bool = False) -> List[ScoredChunk]:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("hybrid_search") as span:
        span.set_attribute("query", query)
        span.set_attribute("candidate_id", candidate_id)
        
        vec_task = vector_search(query, candidate_id, db, k=k*2, document_kind=document_kind, boost_verified=boost_verified)
        ft_task = fulltext_search(query, candidate_id, db, k=k*2, document_kind=document_kind, boost_verified=boost_verified)
        
        vec_results, ft_results = await asyncio.gather(vec_task, ft_task)
        
        # Reciprocal Rank Fusion
        # score = sum(1 / (rank_constant + rank_in_list))
        # Why this rewards cross-list agreement:
        # A chunk appearing in both lists gets the sum of two RRF scores.
        # This additive effect ensures that a chunk ranked moderately in both methods 
        # often beats a chunk ranked highly in only one method, naturally elevating 
        # results with both semantic relevance and exact keyword overlap.
        RANK_CONSTANT = 60
        
        chunk_map = {}
        
        for idx, chunk in enumerate(vec_results):
            rank = idx + 1
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = {"chunk": chunk, "score": 0.0}
            chunk_map[chunk.id]["score"] += 1.0 / (RANK_CONSTANT + rank)
            
        for idx, chunk in enumerate(ft_results):
            rank = idx + 1
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = {"chunk": chunk, "score": 0.0}
            chunk_map[chunk.id]["score"] += 1.0 / (RANK_CONSTANT + rank)
            
        fused = list(chunk_map.values())
        fused.sort(key=lambda x: x["score"], reverse=True)
        
        final_results = []
        for i, item in enumerate(fused[:k]):
            c = item["chunk"]
            c.score = item["score"]
            c.rank = i + 1
            final_results.append(c)
            
        span.set_attribute("results_count", len(final_results))
        return final_results
