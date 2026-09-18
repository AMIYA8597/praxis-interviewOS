import asyncio
import time
import numpy as np
import uuid
import re

from praxis_ai_gateway.retrieval import ScoredChunk, hybrid_search
import praxis_ai_gateway.retrieval as retrieval_module

class MockDB:
    pass

# Generate 50,000 synthetic chunks
print("Generating synthetic DB...")
num_chunks = 50000
dim = 384
np.random.seed(42)
fake_embeddings = np.random.randn(num_chunks, dim)
fake_embeddings /= np.linalg.norm(fake_embeddings, axis=1, keepdims=True)

# Plant our specific fixtures
fake_chunks = []
for i in range(num_chunks):
    content = f"Random content {i}"
    doc_id = "doc1"
    kind = "other"
    verified = True
    
    if i == 1000:
        content = "Built a highly scalable data pipeline using Apache Kafka to process 1M events per second."
        doc_id = "doc_resume"
        kind = "resume"
        # Seeded exact lexical match
    elif i == 2000:
        content = "Improved model accuracy by 15% through careful feature engineering and hyperparameter tuning."
        doc_id = "doc_resume"
        kind = "resume"
        verified = False # Unverified claim!
    elif i == 3000:
        content = "Led the machine learning team to better performance via hyperparameter search, optimizing the learning rate."
        doc_id = "doc_resume"
        kind = "resume"
        verified = True
        
    fake_chunks.append({
        "id": str(uuid.uuid4()),
        "document_id": doc_id,
        "content": content,
        "kind": kind,
        "verified": verified,
        "filename": "seeded_resume.pdf",
        "index": i
    })

# Manually compute embeddings for the seeded chunks to ensure semantic search works
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-en-v1.5')
fake_embeddings[1000] = model.encode([fake_chunks[1000]["content"]], normalize_embeddings=True)[0]
fake_embeddings[2000] = model.encode([fake_chunks[2000]["content"]], normalize_embeddings=True)[0]
fake_embeddings[3000] = model.encode([fake_chunks[3000]["content"]], normalize_embeddings=True)[0]

async def mock_vector_search(query, candidate_id, db, k=10, document_kind=None, boost_verified=False):
    query_vec = model.encode([query], normalize_embeddings=True)[0]
    
    # Simulate DB latency
    await asyncio.sleep(0.015)
    
    sims = np.dot(fake_embeddings, query_vec)
    
    # filter
    valid_indices = []
    for i in range(num_chunks):
        c = fake_chunks[i]
        if document_kind and c["kind"] != document_kind:
            continue
        if boost_verified and not c["verified"]:
            continue
        valid_indices.append(i)
        
    valid_indices = np.array(valid_indices)
    valid_sims = sims[valid_indices]
    
    top_k_rel = np.argsort(valid_sims)[::-1][:k]
    top_k_idx = valid_indices[top_k_rel]
    
    results = []
    for idx in top_k_idx:
        c = fake_chunks[idx]
        results.append(ScoredChunk(id=c["id"], document_id=c["document_id"], content=c["content"], score=float(sims[idx]), original_filename=c["filename"], chunk_index=c["index"]))
    return results

async def mock_fulltext_search(query, candidate_id, db, k=10, document_kind=None, boost_verified=False):
    await asyncio.sleep(0.010)
    query_terms = set(re.findall(r'\w+', query.lower()))
    
    scores = []
    for i in range(num_chunks):
        c = fake_chunks[i]
        if document_kind and c["kind"] != document_kind:
            continue
        if boost_verified and not c["verified"]:
            continue
        
        content_terms = set(re.findall(r'\w+', c["content"].lower()))
        overlap = len(query_terms.intersection(content_terms))
        if overlap > 0:
            scores.append((i, overlap))
            
    scores.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for idx, overlap in scores[:k]:
        c = fake_chunks[idx]
        results.append(ScoredChunk(id=c["id"], document_id=c["document_id"], content=c["content"], score=float(overlap), original_filename=c["filename"], chunk_index=c["index"]))
    return results

retrieval_module.vector_search = mock_vector_search
retrieval_module.fulltext_search = mock_fulltext_search

async def run_benchmark():
    db = MockDB()
    candidate_id = "cand1"
    
    print("\n--- Testing Lexical Exact Match ---")
    query1 = "Apache Kafka pipeline"
    start = time.perf_counter()
    res1 = await hybrid_search(query1, candidate_id, db, k=5, document_kind='resume')
    latency1 = (time.perf_counter() - start) * 1000
    print(f"Latency: {latency1:.2f} ms")
    for r in res1:
        print(f"Score: {r.score:.4f} | {r.content}")
        
    print("\n--- Testing Semantic Paraphrase ---")
    query2 = "A time you made a model perform better"
    start = time.perf_counter()
    res2 = await hybrid_search(query2, candidate_id, db, k=5, document_kind='resume')
    latency2 = (time.perf_counter() - start) * 1000
    print(f"Latency: {latency2:.2f} ms")
    for r in res2:
        print(f"Score: {r.score:.4f} | {r.content}")

    print("\n--- Testing boost_verified Hard Exclusion ---")
    res_verified = await hybrid_search(query2, candidate_id, db, k=5, document_kind='resume', boost_verified=True)
    for r in res_verified:
        print(f"Score: {r.score:.4f} | {r.content}")
        assert "Improved model accuracy by 15%" not in r.content, "Unverified claim leaked!"
    print("Unverified claim successfully excluded.")

    # Latency p50/p95 simulation
    latencies = []
    for _ in range(50):
        start = time.perf_counter()
        await hybrid_search("test query latency", candidate_id, db, k=5)
        latencies.append((time.perf_counter() - start) * 1000)
    
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    print(f"\nLatency over 50 queries against 50k chunks:")
    print(f"p50: {p50:.2f} ms")
    print(f"p95: {p95:.2f} ms")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
