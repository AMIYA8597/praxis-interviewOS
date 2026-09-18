import asyncio
import time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import numpy as np

from praxis_ai_gateway.retrieval import vector_search, fulltext_search, hybrid_search
from praxis_ai_gateway.context_packer import pack_context
from praxis_ai_gateway.embeddings import embed_texts
from praxis_ai_gateway.chunking import chunk_text

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/interviewos"

async def test_hybrid_retrieval():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # Create a candidate
        res = await conn.execute(text("INSERT INTO candidates (id, email, first_name, last_name) VALUES (gen_random_uuid(), 'test_hybrid@example.com', 'Test', 'Hybrid') RETURNING id"))
        candidate_id = res.scalar()
        
        # Create a document
        res = await conn.execute(text("INSERT INTO documents (id, candidate_id, kind, original_filename, processing_status) VALUES (gen_random_uuid(), :cid, 'resume', 'test_resume.pdf', 'ready') RETURNING id"), {"cid": candidate_id})
        doc_id = res.scalar()
        
        # Insert a resume version
        res = await conn.execute(text("INSERT INTO resume_versions (id, candidate_id, document_id) VALUES (gen_random_uuid(), :cid, :doc_id) RETURNING id"), {"cid": candidate_id, "doc_id": doc_id})
        resume_version_id = res.scalar()

        # Resume text
        raw_text = """
        EXPERIENCE
        Senior Engineer at DataCorp
        Built a highly scalable data pipeline using Apache Kafka to process 1M events per second.
        
        Machine Learning Engineer at AI Inc
        Improved model accuracy by 15% through careful feature engineering and hyperparameter tuning.
        
        EDUCATION
        B.S. Computer Science
        """
        
        chunks = chunk_text(raw_text, target_tokens=50, overlap_tokens=10)
        embs = await embed_texts(chunks, normalize=True)
        
        for i, (chunk, emb) in enumerate(zip(chunks, embs)):
            await conn.execute(text("""
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding, embedding_model, embedding_version)
                VALUES (:doc_id, :idx, :content, :emb::vector, 'BAAI/bge-small-en-v1.5', 'v1')
            """), {"doc_id": doc_id, "idx": i, "content": chunk, "emb": str(emb)})

        # Insert unverified claim for testing boost_verified
        await conn.execute(text("""
            INSERT INTO resume_claims (resume_version_id, claim_text, claim_type, verified_by_user)
            VALUES (:rv_id, 'improved model accuracy', 'metric', false)
        """), {"rv_id": resume_version_id})

    # Test 1: Lexical exact terminology (Kafka)
    start_t = time.perf_counter()
    kafka_results = await hybrid_search("Apache Kafka", str(candidate_id), engine, k=5)
    latency_ms = (time.perf_counter() - start_t) * 1000
    print(f"Hybrid search latency (Kafka): {latency_ms:.2f}ms")
    
    assert len(kafka_results) > 0
    assert "Kafka" in kafka_results[0].content
    
    # Test 2: Semantic paraphrase ("time you improved model accuracy")
    start_t = time.perf_counter()
    semantic_results = await hybrid_search("A time you made a model perform better", str(candidate_id), engine, k=5)
    latency_ms = (time.perf_counter() - start_t) * 1000
    print(f"Hybrid search latency (Semantic): {latency_ms:.2f}ms")
    
    assert len(semantic_results) > 0
    assert "Improved model accuracy by 15%" in semantic_results[0].content

    # Test 3: Context Packing
    packed = pack_context(kafka_results, max_tokens=100)
    assert "[source: test_resume.pdf, chunk" in packed
    assert "Apache Kafka" in packed
    
    # Test 4: boost_verified hard exclusion
    # The 'improved model accuracy' chunk should be excluded because of the unverified claim
    verified_results = await hybrid_search("A time you made a model perform better", str(candidate_id), engine, k=5, document_kind='resume', boost_verified=True)
    
    # The chunk containing 'Improved model accuracy' should not be present
    for r in verified_results:
        assert "Improved model accuracy" not in r.content

    print("All tests passed!")


if __name__ == '__main__':
    asyncio.run(test_hybrid_retrieval())
