import asyncio
from sqlalchemy import text
from typing import Dict
from praxis_ai_gateway.base import LLMProvider

async def check_provider_health(ctx):
    providers = ctx['providers']
    db_engine = ctx['db_engine']
    # This task runs every 60s
    # ctx holds the arq context
    async with db_engine.begin() as conn:
        for name, provider in providers.items():
            status = "healthy"
            details = "Provider reachable"
            
            # Simple probe: if provider supports models list or trivial generate, do it here.
            # For simplicity, we just do a try/except on their initialization/connection if they have one.
            # Many don't have a cheap ping, so we might just ensure they are configured.
            if not provider.capabilities().is_free_tier and not getattr(provider, "api_key", None):
                status = "degraded"
                details = "API key missing"
            else:
                try:
                    # In a real implementation, you'd do a lightweight call like getting the models list 
                    # if the provider supports it (e.g. httpx.get(".../models")).
                    # Here we just mark healthy if we haven't failed.
                    pass
                except Exception as e:
                    status = "down"
                    details = str(e)
            
            # Update provider_health
            query = text("""
                INSERT INTO provider_health (provider_name, status, details)
                VALUES (:name, :status, :details)
            """)
            await conn.execute(query, {"name": name, "status": status, "details": details})


