import json
from pathlib import Path
from typing import Any

from pydantic import field_validator

# Импортируем общий конфиг
from src.shared.core.config import ROOT_DIR, CommonSettings


class Settings(CommonSettings):
    """
    Application Configuration (Backend).
    Inherits from CommonSettings (Redis, Logging, Paths).
    """

    # --- Main ---
    PROJECT_NAME: str = "PinLite"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    DEBUG: bool = False

    # Domain settings for generating absolute URLs
    SITE_URL: str = "http://localhost:8000"

    # --- Security ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Database ---
    DATABASE_URL: str
    DB_SCHEMA: str = "fastapi_app"  # PostgreSQL schema for table isolation

    # --- Storage ---
    # Используем ROOT_DIR из shared конфига для построения путей
    UPLOAD_DIR: Path = ROOT_DIR / "data" / "uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5 MB

    # --- Logging Override ---
    # Переопределяем путь к логам, чтобы они падали в data/logs
    log_dir: str = str(ROOT_DIR / "data" / "logs")

    # --- CORS ---
    ALLOWED_ORIGINS: str | list[str] = '["*"]'

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> Any:
        """
        Parses a JSON string of origins into a list.
        """
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @field_validator("SITE_URL")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        """
        Ensure SITE_URL does not end with a slash.
        """
        return v.rstrip("/")


settings = Settings()

# Ensure critical directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# Создаем папку логов (путь берем из settings, так как он теперь str)
Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
