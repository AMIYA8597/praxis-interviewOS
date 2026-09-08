import re
from typing import List

def chunk_text_semantically(text: str, max_tokens: int = 300) -> List[str]:
    """
    Splits text into paragraph-aware chunks rather than blind character splits.
    This prevents mid-sentence fragmentation and improves vector cohesion.
    """
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    
    # Rough token approximation (1 token ~= 4 characters)
    for p in paragraphs:
        if len(current_chunk) + len(p) < (max_tokens * 4):
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
