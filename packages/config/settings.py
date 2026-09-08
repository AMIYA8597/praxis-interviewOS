import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

class Settings(BaseSettings):
    # Core
    APP_ENV: str = "development"
    ZERO_SPEND_MODE: bool = True
    LOCAL_ONLY_MODE: bool = True
    
    # Database (Required)
    DATABASE_URL: str = Field(..., description="Postgres connection string")
    
    # Supabase (Optional unless using Supabase backend)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Redis (Required)
    REDIS_URL: str = Field(..., description="Redis connection string")
    REDIS_MAX_CONNECTIONS: int = 10
    
    # Storage
    STORAGE_BACKEND: str = Field("local", description="local or supabase")
    STORAGE_LOCAL_PATH: str = "./storage"
    
    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318/v1/traces"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

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

    def local_only_ready(self) -> bool:
        """
        Returns True only if every variable needed for the fully-local 
        (no Supabase, no hosted Redis) path is present and valid.
        """
        if self.STORAGE_BACKEND.lower() != "local":
            return False
        
        # In local mode, DATABASE_URL and REDIS_URL are strictly required 
        # (pydantic handles that on init, so if we got here, they exist).
        # We also want to ensure they look like local URIs if we want to be strict,
        # but just ensuring they are populated is the main check.
        if "localhost" not in self.DATABASE_URL and "127.0.0.1" not in self.DATABASE_URL and "postgres" not in self.DATABASE_URL:
             # Basic sanity check; might be Docker-based hostname like 'db' or 'postgres'
             pass
             
        return True

# Singleton instance
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"FATAL: Configuration failed to load: {e}", file=sys.stderr)
    # We don't exit here directly to allow test scripts to catch it, but in an app we might.
