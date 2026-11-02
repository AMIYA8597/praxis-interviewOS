"""
Shared process bootstrap for the API, worker and realtime agent:
logging, tracing and the AI gateway.
"""
import logging
import os
from typing import Optional

from opentelemetry import trace

from backend.app.core.logging_config import setup_structured_logging
from packages.config.settings import Settings

logger = logging.getLogger(__name__)
_tracing_configured = False


def configure_logging(cfg: Settings, service: str) -> None:
    setup_structured_logging(service=service, level=cfg.LOG_LEVEL, fmt=cfg.log_format)


def configure_tracing(cfg: Settings, service: str) -> None:
    """Install an OTLP exporter only when tracing is enabled (never in tests by default)."""
    global _tracing_configured
    if _tracing_configured:
        return
    _tracing_configured = True
    if not cfg.otel_enabled or os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
        return
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": cfg.OTEL_SERVICE_NAME or service}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=cfg.OTEL_EXPORTER_OTLP_ENDPOINT)))
    trace.set_tracer_provider(provider)
    logger.info("tracing_enabled", extra={"otel_endpoint": cfg.OTEL_EXPORTER_OTLP_ENDPOINT})


def build_providers(cfg: Optional[Settings] = None) -> dict:
    """Instantiate every provider whose prerequisites are configured."""
    providers = {}

    def _get_val(k: str) -> Optional[str]:
        return (getattr(cfg, k, None) or os.environ.get(k) or "").strip() or None

    # Ollama is registered only if explicitly enabled or configured as LLM_PROVIDER
    ollama_enabled = os.environ.get("OLLAMA_ENABLED", "").lower() in ("true", "1") or _get_val("LLM_PROVIDER") == "ollama"
    if ollama_enabled:
        try:
            from praxis_ai_gateway.providers.ollama import OllamaProvider
            ollama_url = (getattr(cfg, "OLLAMA_BASE_URL", None) or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434")
            providers["ollama"] = OllamaProvider(base_url=ollama_url)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "ollama", "error_type": type(e).__name__})

    # Groq
    groq_key = _get_val("GROQ_API_KEY")
    if groq_key:
        try:
            from praxis_ai_gateway.providers.groq import GroqProvider
            providers["groq"] = GroqProvider(api_key=groq_key)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "groq", "error_type": type(e).__name__})

    # OpenAI / OpenRouter
    openai_key = _get_val("OPENAI_API_KEY")
    if openai_key:
        try:
            from praxis_ai_gateway.providers.openai import OpenAIProvider
            openai_url = _get_val("OPENAI_BASE_URL")
            providers["openai"] = OpenAIProvider(api_key=openai_key, base_url=openai_url)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "openai", "error_type": type(e).__name__})

    # DeepSeek
    deepseek_key = _get_val("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            from praxis_ai_gateway.providers.deepseek import DeepSeekProvider
            deepseek_url = _get_val("DEEPSEEK_BASE_URL")
            providers["deepseek"] = DeepSeekProvider(api_key=deepseek_key, base_url=deepseek_url)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "deepseek", "error_type": type(e).__name__})

    # Gemini
    gemini_key = _get_val("GEMINI_API_KEY") or _get_val("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from praxis_ai_gateway.providers.gemini import GeminiProvider
            providers["gemini"] = GeminiProvider(api_key=gemini_key)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "gemini", "error_type": type(e).__name__})

    # Anthropic
    anthropic_key = _get_val("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            from praxis_ai_gateway.providers.anthropic import AnthropicProvider
            providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": "anthropic", "error_type": type(e).__name__})

    return providers


def build_gateway(cfg: Settings, redis, session_factory=None, providers: Optional[dict] = None):
    from praxis_ai_gateway.registry import ModelRegistry
    from praxis_ai_gateway.router import GatewayRouter

    registry = ModelRegistry(cfg.MODELS_CONFIG_PATH)
    return GatewayRouter(
        registry=registry,
        providers=providers if providers is not None else build_providers(cfg),
        redis=redis,
        db=None,
        session_factory=session_factory,
    )
