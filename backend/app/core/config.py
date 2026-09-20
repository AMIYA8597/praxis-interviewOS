import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ZERO_SPEND_MODE: bool = os.getenv("ZERO_SPEND_MODE", "True").lower() in ("true", "1", "yes")
    SUPABASE_FREE_TIER_MODE: bool = os.getenv("SUPABASE_FREE_TIER_MODE", "True").lower() in ("true", "1", "yes")
    
    class Config:
        env_file = ".env"

settings = Settings()
