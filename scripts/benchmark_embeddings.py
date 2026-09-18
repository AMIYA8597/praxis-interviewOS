import asyncio
import time
from typing import List

from praxis_ai_gateway.embeddings import embed_texts, EMBEDDING_MODEL_NAME, EMBEDDING_VERSION

async def run_benchmark():
    print(f"Benchmarking Embeddings with {EMBEDDING_MODEL_NAME} ({EMBEDDING_VERSION})")
    # Synthetic sentences
    sentences = [
        "The quick brown fox jumps over the lazy dog." * (i % 5 + 1)
        for i in range(100)
    ]
    
    print(f"Embedding {len(sentences)} synthetic sentences in batches of 32...")
    start_time = time.perf_counter()
    embeddings = await embed_texts(sentences, normalize=True, batch_size=32)
    end_time = time.perf_counter()
    
    total_time = end_time - start_time
    per_text_time = total_time / len(sentences)
    
    print(f"Total time: {total_time:.4f}s")
    print(f"Per-text average: {per_text_time * 1000:.2f}ms")
    
    # Sanity checks
    print("\nRunning Sanity Checks...")
    texts = [
        "Distributed systems rely heavily on message queues like Kafka to decouple microservices and ensure fault tolerance.",
        "Baking bread requires a precise mixture of flour, water, yeast, and salt, followed by adequate proofing time.",
        "A highly decoupled architecture can be achieved using event streaming platforms such as Apache Kafka for fault-tolerant microservice communication."
    ]
    
    start_check = time.perf_counter()
    embs = await embed_texts(texts, normalize=True, batch_size=32)
    print(f"Embedded 3 sanity sentences in {(time.perf_counter() - start_check)*1000:.2f}ms")
    
    import numpy as np
    emb_kafka = np.array(embs[0])
    emb_bread = np.array(embs[1])
    emb_kafka_para = np.array(embs[2])
    
    sim_kafka_bread = np.dot(emb_kafka, emb_bread)
    sim_kafka_para = np.dot(emb_kafka, emb_kafka_para)
    
    print(f"Similarity ('distributed systems/Kafka' vs 'baking bread'): {sim_kafka_bread:.4f}")
    print(f"Similarity ('distributed systems/Kafka' vs paraphrase): {sim_kafka_para:.4f}")
    
    assert sim_kafka_bread < sim_kafka_para, "Sanity check failed: Bread is more similar to Kafka than its paraphrase!"
    assert sim_kafka_para > 0.7, "Sanity check failed: Paraphrase similarity is too low!"
    assert sim_kafka_bread < 0.6, "Sanity check failed: Unrelated similarity is too high!"
    
    print("Sanity checks passed.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
