import os

providers_dir = r"d:\work\interviewOS\packages\ai-gateway\praxis_ai_gateway\providers"

for filename in os.listdir(providers_dir):
    if not filename.endswith(".py") or filename == "__init__.py":
        continue
        
    filepath = os.path.join(providers_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    out_lines = []
    has_imported_helper = False
    
    in_generate = False
    in_structured = False
    in_embed = False
    
    for i, line in enumerate(lines):
        if "from praxis_ai_gateway.base import" in line and not has_imported_helper:
            out_lines.append(line)
            out_lines.append("from praxis_ai_gateway.cancellation_helper import with_cancellation\n")
            has_imported_helper = True
            continue
            
        if line.replace(" ", "").startswith("asyncdefgenerate(self"):
            line = line.replace("generate", "_generate")
            out_lines.append("    async def generate(self, messages, cancellation_token=None, **kw):\n")
            out_lines.append("        return await with_cancellation(self._generate(messages, cancellation_token=None, **kw), cancellation_token)\n\n")
            out_lines.append(line)
            continue
            
        if line.replace(" ", "").startswith("asyncdefstructured(self"):
            line = line.replace("structured", "_structured")
            out_lines.append("    async def structured(self, messages, schema, cancellation_token=None, **kw):\n")
            out_lines.append("        return await with_cancellation(self._structured(messages, schema, cancellation_token=None, **kw), cancellation_token)\n\n")
            out_lines.append(line)
            continue
            
        if line.replace(" ", "").startswith("asyncdefembed(self"):
            line = line.replace("embed", "_embed")
            out_lines.append("    async def embed(self, texts, cancellation_token=None, **kw):\n")
            out_lines.append("        return await with_cancellation(self._embed(texts, cancellation_token=None, **kw), cancellation_token)\n\n")
            out_lines.append(line)
            continue
            
        # Fix stream is_set
        if "cancellation_token.is_set()" in line:
            line = line.replace("is_set()", "is_cancelled()")
            
        out_lines.append(line)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
