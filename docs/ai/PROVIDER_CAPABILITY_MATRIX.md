# PRAXIS InterviewOS — AI Provider Capability Matrix

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Provider Adapter Audit

| Provider | Implemented Adapter | Supported Operations | Auth Model | Structured Output | Streaming | Error Normalization | Status in Repository |
|---|---|---|---|---|---|---|:---:|
| **Google Gemini** | `praxis_ai_gateway.providers.gemini.GeminiProvider` | Generate, Stream, Structured, Health Probe | API Key (`AIza...`) | Schema-constrained JSON mode | Supported via Server-Sent Events | `ProviderAuthError`, `ProviderRateLimitError`, `ProviderServerError` | **VERIFIED & ACTIVE** |
| **Groq** | `praxis_ai_gateway.providers.groq.GroqProvider` | Generate, Stream, Structured, Health Probe | API Key (`gsk_...`) | JSON Mode (`response_format={"type": "json_object"}`) | Supported | Normalizes 401, 429, 503 | **IMPLEMENTED (Unconfigured in test .env)** |
| **OpenAI** | `praxis_ai_gateway.providers.openai.OpenAIProvider` | Generate, Stream, Structured, Health Probe | API Key (`sk-...`) | Native JSON Schema (`strict: true`) | Supported | Standard OpenAI error mapping | **IMPLEMENTED (Paid fallback)** |
| **Anthropic** | `praxis_ai_gateway.providers.anthropic.AnthropicProvider` | Generate, Stream, Structured, Health Probe | API Key (`sk-ant-...`) | Tool call extraction | Supported | Anthropic error mapping | **IMPLEMENTED (Paid fallback)** |
| **DeepSeek** | `praxis_ai_gateway.providers.deepseek.DeepSeekProvider` | Generate, Stream, Structured, Health Probe | API Key (`sk-...`) | JSON mode | Supported | DeepSeek error mapping | **IMPLEMENTED (Paid fallback)** |
| **xAI** | `praxis_ai_gateway.providers.xai.XAIProvider` | Generate, Stream, Structured, Health Probe | API Key (`xai-...`) | JSON mode | Supported | xAI error mapping | **IMPLEMENTED (Paid fallback)** |
| **Ollama** | `praxis_ai_gateway.providers.ollama.OllamaProvider` | Generate, Stream, Structured, Health Probe | Local endpoint (`http://localhost:11434`) | Ollama format=json | Supported | Connection error handling | **IMPLEMENTED (Local-only)** |

---

## 2. Model Alias Routing Architecture

All operations request functional aliases defined in `config/models.yaml`:
1. `fast_classify`: Groq `llama-3.1-8b-instant` -> Gemini `gemini-2.5-flash-lite` -> OpenAI `gpt-4o-mini`.
2. `reasoning`: Groq `llama-3.3-70b-versatile` -> Gemini `gemini-2.5-flash-lite` / `gemini-3.5-flash` -> OpenAI `gpt-4o-mini`.
3. `deep_reasoning`: Groq `llama-3.3-70b-versatile` -> Gemini `gemini-2.5-flash-lite` -> OpenAI `gpt-4o` -> Anthropic `claude-3-5-sonnet`.
4. `question_generation`: Groq `llama-3.3-70b-versatile` -> Gemini `gemini-2.5-flash-lite` -> OpenAI `gpt-4o-mini`.
5. `answer_evaluation`: Groq `llama-3.3-70b-versatile` -> Gemini `gemini-2.5-flash-lite` -> OpenAI `gpt-4o` -> Anthropic `claude-3-5-sonnet`.
