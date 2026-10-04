import logging

from sqlalchemy import text

logger = logging.getLogger("praxis.ai_gateway")


async def check_provider_health(ctx):
    """Periodic (cron) snapshot of provider configuration health into provider_health."""
    providers = ctx.get("providers", {})
    db_engine = ctx["db_engine"]
    rows = []
    for name, provider in providers.items():
        try:
            caps = provider.capabilities()
            # Local providers need no key; keyed providers are "open" (unusable) without one.
            needs_key = hasattr(provider, "api_key")
            configured = caps.is_local or not needs_key or bool(getattr(provider, "api_key", None))
            state = "closed" if configured else "open"
        except Exception as e:
            logger.warning("provider_health_probe_failed", extra={"provider": name, "error_type": type(e).__name__})
            state = "open"
        rows.append({"provider": name, "capability": "generate", "state": state})
    if not rows:
        return
    try:
        async with db_engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO provider_health (provider, capability, state, checked_at)
                    VALUES (:provider, :capability, :state, now())
                """),
                rows,
            )
    except Exception as e:
        logger.warning("provider_health_write_failed", extra={"error_type": type(e).__name__})
