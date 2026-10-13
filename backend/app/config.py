import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    APP_NAME: str = "Mafia42 Collection Journal API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "m42_super_secret_jwt_key_change_in_production_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database URL: default SQLite for local dev, PostgreSQL for production
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./mafia42.db")

    # Initial Owner Setup
    INITIAL_OWNER_EMAIL: str = os.getenv("INITIAL_OWNER_EMAIL", "owner@mafia42journal.com")
    INITIAL_OWNER_USERNAME: str = os.getenv("INITIAL_OWNER_USERNAME", "Owner")
    INITIAL_OWNER_PASSWORD: str = os.getenv("INITIAL_OWNER_PASSWORD", "OwnerJournal2026!Secure")

    # CORS — supports a JSON list string from env var OR defaults for local dev.
    # In production set: CORS_ORIGINS=["https://your-app.onrender.com"]
    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", "")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # Treat as comma-separated string
                return [o.strip() for o in raw.split(",") if o.strip()]
        # Default: allow all (suitable for first-deploy testing; tighten after URL is known)
        return ["*"]

settings = Settings()
