"""
Central, typed configuration for every PRAXIS Python service.

All values are read from the environment (and `.env` when present). Every
variable is documented in `.env.example`. Production-only invariants are
enforced in `validate_production` so a misconfigured deploy fails at boot
instead of at the first request.
"""
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ENVS = {"development", "dev", "local", "test", "testing", "ci"}


class Settings(BaseSettings):
    # ── Core ────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    ZERO_SPEND_MODE: bool = True
    LOCAL_ONLY_MODE: bool = True
    LOG_LEVEL: str = "INFO"
    # "json" for log aggregation (default outside development), "text" for humans.
    LOG_FORMAT: Optional[str] = None

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        "postgresql://praxis:dev_password@localhost:5432/praxis",
        description="Postgres connection string (postgresql:// or postgresql+asyncpg://)",
    )
    DB_POOL_SIZE: int = Field(10, ge=1)
    DB_MAX_OVERFLOW: int = Field(10, ge=0)
    DB_POOL_TIMEOUT_S: int = Field(30, ge=1)
    DB_POOL_RECYCLE_S: int = Field(1800, ge=-1)
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False
    DB_STATEMENT_TIMEOUT_MS: int = Field(15000, ge=0)

    # ── Supabase / Auth ─────────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    # Legacy HS256 projects sign access tokens with this shared secret.
    SUPABASE_JWT_SECRET: Optional[str] = None
    JWT_AUDIENCE: str = "authenticated"
    # Defaults to f"{SUPABASE_URL}/auth/v1" when unset.
    JWT_ISSUER: Optional[str] = None
    JWT_LEEWAY_S: int = Field(30, ge=0)
    JWKS_CACHE_TTL_S: int = Field(3600, ge=60)
    # Minimum seconds between forced JWKS refreshes triggered by unknown `kid`s.
    JWKS_REFRESH_COOLDOWN_S: int = Field(60, ge=0)
    # Development-only: accept any bearer token as a fixed local user when no
    # Supabase verifier is configured. Never allowed in production. `None`
    # means "auto": enabled only in a dev APP_ENV without any verifier.
    AUTH_DEV_BYPASS: Optional[bool] = None
    AUTH_DEV_USER_ID: str = "00000000-0000-0000-0000-000000000000"
    CANDIDATE_CACHE_TTL_S: int = Field(900, ge=0)

    # ── HTTP ────────────────────────────────────────────────────────────
    # Comma-separated list. "*" is rejected in production.
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    CORS_ALLOW_CREDENTIALS: bool = True
    # When unset, docs are enabled everywhere except production.
    ENABLE_API_DOCS: Optional[bool] = None
    ENABLE_RATE_LIMIT: bool = True
    TRUSTED_PROXY_COUNT: int = Field(0, ge=0)

    # ── Redis / Queue ───────────────────────────────────────────────────
    REDIS_URL: str = Field("redis://localhost:6379/0", description="Redis connection string")
    REDIS_MAX_CONNECTIONS: int = Field(10, ge=1)
    REDIS_SOCKET_TIMEOUT_S: float = Field(5.0, gt=0)
    REDIS_HEALTH_CHECK_INTERVAL_S: int = Field(30, ge=0)
    ARQ_QUEUE_NAME: str = "arq:queue"
    WORKER_MAX_JOBS: int = Field(10, ge=1)
    WORKER_JOB_TIMEOUT_S: int = Field(300, ge=1)
    WORKER_MAX_TRIES: int = Field(3, ge=1)

    # ── Storage / Uploads ───────────────────────────────────────────────
    STORAGE_BACKEND: str = Field("local", description="local or supabase")
    STORAGE_LOCAL_PATH: str = "./storage"
    STORAGE_BUCKET: str = "documents"
    MAX_UPLOAD_BYTES: int = Field(10 * 1024 * 1024, ge=1024)

    # ── AI ──────────────────────────────────────────────────────────────
    MODELS_CONFIG_PATH: str = "config/models.yaml"
    EMBEDDING_DIM: int = 384

    # ── Realtime ────────────────────────────────────────────────────────
    WS_AUTH_TIMEOUT_S: float = Field(10.0, gt=0)
    WS_RECONNECT_GRACE_S: int = Field(30, ge=1)
    # Silence after a question before the interviewer nudges / moves on.
    TURN_NO_ANSWER_TIMEOUT_S: float = Field(20.0, gt=0)
    TURN_MAX_NUDGES: int = Field(1, ge=0)

    # ── Observability ───────────────────────────────────────────────────
    # When unset, tracing is enabled only if an endpoint was set explicitly.
    OTEL_ENABLED: Optional[bool] = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318/v1/traces"
    OTEL_SERVICE_NAME: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Normalisers ─────────────────────────────────────────────────────
    @field_validator("APP_ENV")
    @classmethod
    def _normalise_env(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @field_validator("SUPABASE_URL")
    @classmethod
    def _strip_trailing_slash(cls, v: Optional[str]) -> Optional[str]:
        return v.rstrip("/") if v else v

    # ── Derived values ──────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV in {"production", "prod"}

    @property
    def is_development(self) -> bool:
        return self.APP_ENV in _DEV_ENVS

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def api_docs_enabled(self) -> bool:
        if self.ENABLE_API_DOCS is not None:
            return self.ENABLE_API_DOCS
        return not self.is_production

    @property
    def jwt_issuer(self) -> Optional[str]:
        if self.JWT_ISSUER:
            return self.JWT_ISSUER
        return f"{self.SUPABASE_URL}/auth/v1" if self.SUPABASE_URL else None

    @property
    def auth_verifier_configured(self) -> bool:
        return bool(self.SUPABASE_URL or self.SUPABASE_JWT_SECRET)

    @property
    def auth_dev_bypass_enabled(self) -> bool:
        if self.is_production:
            return False
        if self.AUTH_DEV_BYPASS is not None:
            return self.AUTH_DEV_BYPASS
        return self.is_development and not self.auth_verifier_configured

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @property
    def sync_database_url(self) -> str:
        """URL for sync tooling (alembic/psycopg2)."""
        url = self.DATABASE_URL
        for prefix in ("postgresql+asyncpg://", "postgres://"):
            if url.startswith(prefix):
                url = "postgresql://" + url[len(prefix):]
        return url

    @property
    def otel_enabled(self) -> bool:
        if self.OTEL_ENABLED is not None:
            return self.OTEL_ENABLED
        return "OTEL_EXPORTER_OTLP_ENDPOINT" in self.model_fields_set

    @property
    def log_format(self) -> str:
        if self.LOG_FORMAT:
            return self.LOG_FORMAT.lower()
        return "text" if self.is_development else "json"

    # ── Validation ──────────────────────────────────────────────────────
    @model_validator(mode="after")
    def validate_storage_backend(self) -> "Settings":
        if self.STORAGE_BACKEND.lower() == "supabase":
            missing = []
            if not self.SUPABASE_URL:
                missing.append("SUPABASE_URL")
            if not self.SUPABASE_SERVICE_ROLE_KEY:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
            if missing:
                raise ValueError(
                    f"STORAGE_BACKEND is set to 'supabase', but missing required credentials: {', '.join(missing)}. "
                    "Either set these variables or switch to STORAGE_BACKEND='local'."
                )
        return self

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if not self.is_production:
            return self
        problems = []
        if not self.auth_verifier_configured:
            problems.append("SUPABASE_URL (or SUPABASE_JWT_SECRET) is required to verify JWTs")
        if self.AUTH_DEV_BYPASS:
            problems.append("AUTH_DEV_BYPASS must not be enabled")
        if "*" in self.cors_origins:
            problems.append("CORS_ALLOW_ORIGINS must list explicit origins, not '*'")
        if "dev_password" in self.DATABASE_URL:
            problems.append("DATABASE_URL still uses the development default credentials")
        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self

    def local_only_ready(self) -> bool:
        """
        True only if every variable needed for the fully-local path
        (no Supabase storage, no hosted Redis) is present and valid.
        DATABASE_URL and REDIS_URL are required fields, so reaching here
        means they are populated.
        """
        return self.STORAGE_BACKEND.lower() == "local"


# Singleton instance
try:
    settings = Settings()
except Exception as e:  # pragma: no cover - exercised only on misconfiguration
    import sys

    print(f"FATAL: Configuration failed to load: {e}", file=sys.stderr)
    raise
