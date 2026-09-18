import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_VERSION = "v1"

_model = None
_executor = ThreadPoolExecutor(max_workers=1)

def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def _embed_batch(texts: List[str], normalize: bool, batch_size: int) -> List[List[float]]:
    _load_model()
    # model.encode returns a numpy array. We need to convert it to a list of lists.
    # We specify normalize_embeddings explicitly.
    embeddings = _model.encode(texts, batch_size=batch_size, normalize_embeddings=normalize)
    return embeddings.tolist()

async def embed_texts(texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
    """
    Embeds a list of texts using the local embedding model.
    Runs on a separate thread to prevent blocking the asyncio event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _embed_batch, texts, normalize, batch_size)
