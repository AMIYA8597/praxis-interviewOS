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


def build_providers() -> dict:
    """Instantiate every provider whose prerequisites are configured."""
    from praxis_ai_gateway.providers.ollama import OllamaProvider

    providers = {"ollama": OllamaProvider(base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))}
    optional = {
        "groq": ("GROQ_API_KEY", "praxis_ai_gateway.providers.groq", "GroqProvider"),
        "openai": ("OPENAI_API_KEY", "praxis_ai_gateway.providers.openai", "OpenAIProvider"),
        "anthropic": ("ANTHROPIC_API_KEY", "praxis_ai_gateway.providers.anthropic", "AnthropicProvider"),
    }
    for name, (env_key, module, cls_name) in optional.items():
        if not os.environ.get(env_key):
            continue
        try:
            import importlib

            providers[name] = getattr(importlib.import_module(module), cls_name)()
        except Exception as e:
            logger.warning("provider_init_failed", extra={"provider": name, "error_type": type(e).__name__})
    return providers


def build_gateway(cfg: Settings, redis, session_factory=None, providers: Optional[dict] = None):
    from praxis_ai_gateway.registry import ModelRegistry
    from praxis_ai_gateway.router import GatewayRouter

    registry = ModelRegistry(cfg.MODELS_CONFIG_PATH)
    return GatewayRouter(
        registry=registry,
        providers=providers if providers is not None else build_providers(),
        redis=redis,
        db=None,
        session_factory=session_factory,
    )
