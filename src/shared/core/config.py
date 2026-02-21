import os
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем корень проекта
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"


class CommonSettings(BaseSettings):
    """
    Базовые настройки, общие для всех сервисов (Backend, Bot, Worker).
    """

    # --- Mode ---
    debug: bool = True  # True = development, False = production

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- Redis Keys ---
    redis_site_settings_key: str = "site_settings_hash"

    # --- Logging ---
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # --- System ---
    system_user_id: int = 2_000_000_000

    @property
    def is_inside_docker(self) -> bool:
        """Определяет, запущен ли код внутри Docker-контейнера."""
        return os.path.exists("/.dockerenv")

    @property
    def effective_redis_host(self) -> str:
        if self.redis_host != "localhost":
            return self.redis_host

        return "redis" if self.is_inside_docker else "localhost"

    @property
    def redis_url(self) -> str:
        host = self.effective_redis_host

        # Очищаем пароль от кавычек, если они случайно попали, и экранируем спецсимволы
        password = self.redis_password
        if password:
            password = password.strip("'\"").strip()

        if password:
            # quote_plus заэкранирует '*' и другие символы для корректного URL
            encoded_password = quote_plus(password)
            return f"redis://:{encoded_password}@{host}:{self.redis_port}"

        return f"redis://{host}:{self.redis_port}"

    @property
    def is_production(self) -> bool:
        return not self.debug

    @property
    def is_development(self) -> bool:
        return self.debug

    # Логи
    @property
    def log_file_debug(self) -> str:
        return f"{self.log_dir}/debug.log"

    @property
    def log_file_errors(self) -> str:
        return f"{self.log_dir}/errors.json"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )
