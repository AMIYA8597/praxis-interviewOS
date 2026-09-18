from typing import List
from praxis_ai_gateway.retrieval import ScoredChunk
from praxis_ai_gateway.chunking import count_tokens

def pack_context(chunks: List[ScoredChunk], max_tokens: int) -> str:
    """
    Greedily includes highest-scored chunks until the token budget is reached.
    Formats them with clear per-chunk provenance markers.
    """
    packed_text = []
    current_tokens = 0
    
    for chunk in chunks:
        # Format the chunk with provenance marker
        formatted_chunk = f"[source: {chunk.original_filename}, chunk {chunk.chunk_index}]\n{chunk.content}\n"
        chunk_tokens = count_tokens(formatted_chunk)
        
        if current_tokens + chunk_tokens <= max_tokens:
            packed_text.append(formatted_chunk)
            current_tokens += chunk_tokens
        else:
            # Token budget reached
            break
            
    return "\n".join(packed_text)
