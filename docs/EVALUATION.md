# Continuous Evaluation & Benchmarking

## Regression Discipline
To maintain realtime performance, **any change to `prompts/` or model routing aliases MUST be run against `tests/fixtures/eval_set/eval_suite.json` before merge.** 
A model upgrade that improves reasoning quality but pushes the `TTS First-Token` latency past 250ms is considered a regression for the Realtime Audio path and must be explicitly gated.

## Core Metrics Tracked
- **Domain Classification Accuracy**: Percentage of inputs correctly binned into Coding/System Design/Behavioral.
- **Grounding Precision**: Fraction of generated LLM claims that contain a mathematically valid `evidence_source_id` matching the RAG graph.
- **False-Positive Turn End**: Rate of the VAD incorrectly triggering the semantic evaluator mid-sentence.
- **Barge-in Latency (p95)**: Must remain under 200ms to feel conversational.
- **Provider Fallback Rate**: Tracked via Jaeger; how often Groq falls back to Gemini or Ollama due to rate limits.
