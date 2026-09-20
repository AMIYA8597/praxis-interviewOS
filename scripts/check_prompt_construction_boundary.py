import os
import sys
import re

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    excluded_dirs = [
        os.path.join(root_dir, ".venv"),
        os.path.join(root_dir, "node_modules"),
        os.path.join(root_dir, ".git")
    ]
    
    # Check for router.route or gateway. calls
    call_pattern = re.compile(r"\.(route|generate|stream|structured)\(")
    
    # Check for f-strings or .format
    suspicious_patterns = [
        re.compile(r"prompt\s*=\s*f[\"']"),
        re.compile(r"content\[[\"']\]\s*:\s*f[\"']"),
        re.compile(r"\.format\(")
    ]
    
    violations = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if any(dirpath.startswith(excl) for excl in excluded_dirs):
            continue
            
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
                
            if filename == "prompt_builder.py" or filename.startswith("test_"):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                if call_pattern.search(line):
                    start = max(0, i - 5)
                    end = min(len(lines), i + 6)
                    
                    suspicious = False
                    for j in range(start, end):
                        ctx_line = lines[j]
                        if any(p.search(ctx_line) for p in suspicious_patterns):
                            suspicious = True
                            break
                            
                    if suspicious:
                        print(f"::warning file={os.path.relpath(filepath, root_dir)},line={i+1}::Suspicious prompt construction detected.")
                        print(f"  Found router/gateway call near f-string or .format(). Use PromptBuilder instead.")
                        print(f"  Context: {line.strip()}")
                        violations += 1
                        
    if violations > 0:
        print(f"Found {violations} suspicious prompt construction(s).")
        sys.exit(1)
    else:
        print("Prompt construction boundary check passed: No suspicious inline prompt construction found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
