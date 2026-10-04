"""Async engine/session factory with production pooling settings."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from packages.config.settings import Settings, settings as default_settings


def create_engine(cfg: Optional[Settings] = None, *, url: Optional[str] = None) -> AsyncEngine:
    cfg = cfg or default_settings
    url = url or cfg.async_database_url
    kwargs = {"echo": cfg.DB_ECHO}
    if url.startswith("postgresql"):
        kwargs.update(
            pool_size=cfg.DB_POOL_SIZE,
            max_overflow=cfg.DB_MAX_OVERFLOW,
            pool_timeout=cfg.DB_POOL_TIMEOUT_S,
            pool_recycle=cfg.DB_POOL_RECYCLE_S,
            pool_pre_ping=cfg.DB_POOL_PRE_PING,
        )
        if "asyncpg" in url and cfg.DB_STATEMENT_TIMEOUT_MS:
            kwargs["connect_args"] = {
                "server_settings": {"statement_timeout": str(cfg.DB_STATEMENT_TIMEOUT_MS)},
            }
    return create_async_engine(url, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Lazily-created module-level engine for scripts that need a session outside
# the FastAPI app (the app builds its own in lifespan).
_engine: Optional[AsyncEngine] = None
_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _factory
    if _factory is None:
        _engine = create_engine()
        _factory = create_session_factory(_engine)
    return _factory


def AsyncSessionLocal() -> AsyncSession:  # noqa: N802 - kept for backwards compatibility
    return _get_factory()()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
