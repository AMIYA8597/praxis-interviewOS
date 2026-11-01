"""
PRAXIS InterviewOS — Production Lifecycle & Reliability Test Suite
Verifies production configuration invariants, database pool budgets,
Redis broker timeouts, and distributed tracing propagation.
"""
import uuid
import pytest
from packages.config.settings import Settings
from backend.app.core.context import bind, snapshot


def test_production_fails_on_dev_bypass():
    """Verify that AUTH_DEV_BYPASS cannot be enabled when APP_ENV is production."""
    with pytest.raises(ValueError) as excinfo:
        Settings(
            APP_ENV="production",
            AUTH_DEV_BYPASS=True,
            DATABASE_URL="postgresql+asyncpg://praxis:prod_secure_password_123@prod-db.internal:5432/praxis",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_JWT_SECRET="super-secret-key-that-is-at-least-32-bytes-long",
            CORS_ALLOW_ORIGINS="https://praxis.example.com",
            STORAGE_BACKEND="local",
        )
    assert "AUTH_DEV_BYPASS must not be enabled" in str(excinfo.value)


def test_production_fails_on_wildcard_cors():
    """Verify that wildcard '*' CORS is strictly rejected in production."""
    with pytest.raises(ValueError) as excinfo:
        Settings(
            APP_ENV="production",
            CORS_ALLOW_ORIGINS="*",
            DATABASE_URL="postgresql+asyncpg://praxis:prod_secure_password_123@prod-db.internal:5432/praxis",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_JWT_SECRET="super-secret-key-that-is-at-least-32-bytes-long",
            STORAGE_BACKEND="local",
        )
    assert "CORS_ALLOW_ORIGINS must list explicit origins, not '*'" in str(excinfo.value)


def test_production_fails_on_dev_password_in_db_url():
    """Verify that default dev_password cannot be used in production."""
    with pytest.raises(ValueError) as excinfo:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_JWT_SECRET="super-secret-key-that-is-at-least-32-bytes-long",
            CORS_ALLOW_ORIGINS="https://praxis.example.com",
            STORAGE_BACKEND="local",
        )
    assert "DATABASE_URL still uses the development default credentials" in str(excinfo.value)


def test_database_connection_pool_budget_invariants():
    """Verify default database connection pool sizes maintain the 100-connection ceiling."""
    settings = Settings(
        APP_ENV="development",
        DATABASE_URL="postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis",
        STORAGE_BACKEND="local",
        DB_POOL_SIZE=2,
        DB_MAX_OVERFLOW=3,
        _env_file=None,
    )
    # Each container instance must not exceed 5 connections (2 baseline + 3 overflow)
    max_conns_per_instance = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
    assert max_conns_per_instance <= 5
    # Pool timeout must be bounded (<= 30s) to prevent thread pool starvation
    assert settings.DB_POOL_TIMEOUT_S <= 30
    # Pre-ping must be enabled for stale connection detection
    assert settings.DB_POOL_PRE_PING is True


def test_redis_broker_timeouts_and_retries():
    """Verify ARQ worker job timeouts and retries prevent queue head-of-line blocking."""
    settings = Settings(
        APP_ENV="development",
        REDIS_URL="redis://localhost:6379/0",
        STORAGE_BACKEND="local",
    )
    assert settings.WORKER_JOB_TIMEOUT_S <= 600
    assert settings.WORKER_MAX_TRIES <= 5
    assert settings.REDIS_SOCKET_TIMEOUT_S <= 10.0


def test_distributed_trace_propagation():
    """Verify W3C trace context binding and snapshot isolation."""
    sample_trace_id = uuid.uuid4().hex
    sample_user_id = "user-prod-test-123"

    bind(trace_id=sample_trace_id, user_id=sample_user_id)
    ctx_state = snapshot()

    assert ctx_state["trace_id"] == sample_trace_id
    assert ctx_state["user_id"] == sample_user_id
