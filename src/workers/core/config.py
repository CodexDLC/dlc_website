from pydantic import Field

from src.shared.core.config import CommonSettings


class WorkerSettings(CommonSettings):
    """
    Настройки для Notification Worker (arq).
    """

    # --- Email (SMTP) ---
    # All SMTP fields must be set via .env (no hardcoded defaults for host/user/password)
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 465
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_USE_TLS: bool = True

    # --- Templates ---
    TEMPLATES_DIR: str = "src/workers/templates"

    # --- ARQ Configuration ---
    arq_max_jobs: int = 10
    arq_job_timeout: int = 60
    arq_keep_result: int = 60

    # --- Redis (Internal field for ENV) ---
    # We use Field(alias=...) to allow setting via REDIS_URL in .env
    redis_url_env: str | None = Field(default=None, alias="REDIS_URL")

    @property
    def arq_redis_settings(self):
        """
        Возвращает настройки Redis для arq.
        """
        from arq.connections import RedisSettings

        return RedisSettings(
            host=self.effective_redis_host,
            port=self.redis_port,
            password=self.redis_password,
        )
