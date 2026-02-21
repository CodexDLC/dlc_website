import json

from loguru import logger as log
from pydantic import Field, field_validator

from src.shared.core.config import CommonSettings


class BotSettings(CommonSettings):
    """
    Configuration settings for the Telegram Bot.
    """

    # --- Bot ---
    bot_token: str

    # --- Channels & Topics ---
    telegram_admin_channel_id: int | None = None
    telegram_notification_topic_id: int = 1
    telegram_topics: dict[str, int] = {}

    @field_validator("telegram_topics", mode="before")
    @classmethod
    def parse_telegram_topics(cls, v):
        """
        Parses a JSON string from an environment variable into a dictionary.

        This handles multiple input formats, including a valid JSON string,
        an existing dictionary, or an empty value (None or empty string),
        returning a dictionary in all cases.

        Examples:
        - String: '{"hair": 2, "nails": 4}' -> dict {"hair": 2, "nails": 4}
        - Already a dict: {"hair": 2} -> {"hair": 2}
        - Empty value: None or "" -> {}
        """
        if isinstance(v, str):
            if not v.strip():
                return {}
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                log.warning(f"TELEGRAM_TOPICS is not a dict after parsing: {type(parsed)}")
                return {}
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse TELEGRAM_TOPICS as JSON: {e}")
                return {}
        return v or {}

    # --- Roles (ENV) ---
    superuser_ids: str = ""
    owner_ids: str = ""

    # --- Data mode ---
    # "api"    — telegram_bot talks to FastAPI/Django backend via REST
    # "direct" — telegram_bot has its own infrastructure
    BOT_DATA_MODE: str = "api"

    # --- Database (only when BOT_DATA_MODE=direct) ---
    DATABASE_URL: str | None = None
    DB_SCHEMA: str = "bot_app"

    # --- Backend API (Internal field for ENV) ---
    # We use Field(alias=...) to allow setting via BACKEND_API_URL in .env
    backend_api_url_env: str = Field(default="http://localhost:8000", alias="BACKEND_API_URL")
    backend_api_key: str | None = Field(default=None, alias="BACKEND_API_KEY")
    backend_api_timeout: float = 10.0

    @property
    def api_url(self) -> str:
        """
        Smart determination of the backend URL.
        If a custom URL is set in .env (not localhost), use it.
        Otherwise, choose between localhost and the service name in Docker.
        """
        url = self.backend_api_url_env

        # If URL is explicitly set and it's not the default localhost, return it
        if url and "localhost" not in url and "127.0.0.1" not in url:
            return url.rstrip("/")

        # Auto-detection for Docker/Local
        base = "http://localhost:8000" if self.debug else "http://backend:8000"
        return base

    @property
    def backend_api_url(self) -> str:
        """Alias for api_url for backwards compatibility."""
        return self.api_url

    @property
    def superuser_ids_list(self) -> list[int]:
        return self._parse_ids(self.superuser_ids)

    @property
    def owner_ids_list(self) -> list[int]:
        return self._parse_ids(self.owner_ids)

    @property
    def roles(self) -> dict[str, list[int]]:
        superusers = self.superuser_ids_list
        owners = self.owner_ids_list
        return {
            "superuser": superusers,
            "owner": list(set(owners + superusers)),
            "admin": list(set(owners + superusers)),
        }

    def _parse_ids(self, ids_str: str) -> list[int]:
        if not ids_str:
            return []
        try:
            return [int(x.strip()) for x in ids_str.split(",") if x.strip()]
        except ValueError:
            log.warning(f"BotSettings | Failed to parse IDs='{ids_str}'. Check .env format.")
            return []
