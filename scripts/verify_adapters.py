import asyncio
import os
import sys

# Ensure packages are in PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "packages", "ai-gateway"))

from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.providers.ollama import OllamaProvider
from praxis_ai_gateway.providers.groq import GroqProvider
from praxis_ai_gateway.providers.gemini import GeminiProvider

async def main():
    messages = [LLMMessage(role="user", content="Respond with exactly 'Hello PRAXIS'")]
    
    results = []
    
    print("Verifying Ollama (local)...")
    try:
        ollama = OllamaProvider()
        resp = await ollama.generate(messages)
        results.append(f"**Ollama Response**: {resp.text.strip()} (Latency: {resp.latency_ms:.1f}ms, Model: {resp.model})")
        print("Ollama: Success")
    except Exception as e:
        results.append(f"**Ollama Response**: FAILED ({e})")
        print(f"Ollama: Failed - {e}")
        
    print("Verifying Groq...")
    if os.environ.get("GROQ_API_KEY"):
        try:
            groq = GroqProvider()
            resp = await groq.generate(messages)
            results.append(f"**Groq Response**: {resp.text.strip()} (Latency: {resp.latency_ms:.1f}ms, Model: {resp.model})")
            print("Groq: Success")
        except Exception as e:
            results.append(f"**Groq Response**: FAILED ({e})")
            print(f"Groq: Failed - {e}")
    else:
        results.append("**Groq Response**: SKIPPED (GROQ_API_KEY not set)")
        print("Groq: Skipped")
        
    print("Verifying Gemini...")
    if os.environ.get("GEMINI_API_KEY"):
        try:
            gemini = GeminiProvider()
            resp = await gemini.generate(messages)
            results.append(f"**Gemini Response**: {resp.text.strip()} (Latency: {resp.latency_ms:.1f}ms, Model: {resp.model})")
            print("Gemini: Success")
        except Exception as e:
            results.append(f"**Gemini Response**: FAILED ({e})")
            print(f"Gemini: Failed - {e}")
    else:
        results.append("**Gemini Response**: SKIPPED (GEMINI_API_KEY not set)")
        print("Gemini: Skipped")

    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "TOOL_VERIFICATION.md")
    with open(doc_path, "a") as f:
        f.write("\n\n## Phase 2.5 Adapter Verification\n\n")
        f.write("\n".join(results))
        f.write("\n")
        
    print(f"\nVerification results appended to docs/TOOL_VERIFICATION.md")

if __name__ == "__main__":
    asyncio.run(main())
