import tiktoken
import re

def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text, disallowed_special=()))

def chunk_text(text: str, target_tokens: int = 300, overlap_tokens: int = 50) -> list[str]:
    """
    Chunks text into roughly target_tokens, with an overlap of overlap_tokens.
    Splits by paragraph first, then falls back to sentences if a paragraph is too long.
    Never splits mid-sentence.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    
    # 1. Split into paragraphs
    raw_paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
    
    # 2. Break down oversized paragraphs into sentences
    units = [] # atomic units to form chunks (either paragraphs or sentences)
    for p in paragraphs:
        if count_tokens(p) <= target_tokens:
            units.append(p)
        else:
            # Paragraph too large, split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', p)
            for s in sentences:
                s = s.strip()
                if s:
                    # Even if a sentence is too large, we keep it as a unit 
                    # to strictly avoid mid-sentence splits.
                    units.append(s)
                    
    # 3. Assemble chunks
    chunks = []
    current_chunk_units = []
    current_chunk_tokens = 0
    
    i = 0
    while i < len(units):
        unit = units[i]
        unit_tokens = count_tokens(unit)
        
        # If adding this unit exceeds the target and we already have units, finalize the chunk
        if current_chunk_tokens + unit_tokens > target_tokens and current_chunk_units:
            chunks.append("\n\n".join(current_chunk_units))
            
            # Start a new chunk with overlap
            # Backtrack to find how many units we can include as overlap
            overlap_units = []
            overlap_count = 0
            # iterate backwards over current_chunk_units
            for prev_unit in reversed(current_chunk_units):
                prev_toks = count_tokens(prev_unit)
                if overlap_count + prev_toks <= overlap_tokens:
                    overlap_units.insert(0, prev_unit)
                    overlap_count += prev_toks
                else:
                    break
            
            # If a single unit is larger than overlap_tokens, we might get an empty overlap.
            # To ensure progress, we don't force overlap if it means taking 0 units,
            # or if the overlap contains ALL the units of the previous chunk (to avoid infinite loops).
            if len(overlap_units) == len(current_chunk_units):
                overlap_units = overlap_units[1:] # Drop at least one to guarantee forward progress
                
            current_chunk_units = overlap_units
            current_chunk_tokens = sum(count_tokens(u) for u in current_chunk_units)
            # Do not increment i, we need to process the current unit again in the new chunk
        else:
            current_chunk_units.append(unit)
            current_chunk_tokens += unit_tokens
            i += 1

    # Add the final chunk
    if current_chunk_units:
        chunks.append("\n\n".join(current_chunk_units))
        
    return chunks
