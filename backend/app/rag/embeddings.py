from sentence_transformers import SentenceTransformer
import numpy as np

# Load model lazily to avoid blocking startup
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # Use BAAI/bge-small-en-v1.5 as the default local free-first model
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _model

def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    # model.encode returns a numpy array, we cast to list of floats for pgvector
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
