import os
import sys
import re

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Directories to exclude
    excluded_dirs = [
        os.path.join(root_dir, "packages", "ai-gateway", "praxis_ai_gateway", "providers"),
        os.path.join(root_dir, ".venv"),
        os.path.join(root_dir, "node_modules"),
        os.path.join(root_dir, ".git")
    ]
    
    # We want to exclude test files if they just mention strings, but literal `import` statements in tests 
    # might be caught. To be safe, we can exclude tests/ entirely or just check Python files and look for AST/regex imports.
    # The prompt says: "EXCLUDING test fixture files".
    
    # Regexes for forbidden imports
    # Matching: `import openai`, `from openai import ...`, `import openai.something`
    forbidden_pattern = re.compile(r"^\s*(?:import|from)\s+(openai|anthropic|google\.generativeai|groq|deepseek|xai)\b", re.MULTILINE)
    
    violations = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out excluded directories
        if any(dirpath.startswith(excl) for excl in excluded_dirs):
            continue
            
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            # Optionally skip tests if needed, but let's just check all non-excluded .py files
            # test files usually don't import provider SDKs directly either, they import the adapter or mock it via respx.
            
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if forbidden_pattern.search(line):
                        violations.append(f"{os.path.relpath(filepath, root_dir)}:{i}: {line.strip()}")
                        
    if violations:
        print("ERROR: Found forbidden provider SDK imports outside the ai-gateway providers layer:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("Gateway boundary check passed: No direct provider SDK imports found outside the providers layer.")
        sys.exit(0)

if __name__ == "__main__":
    main()
