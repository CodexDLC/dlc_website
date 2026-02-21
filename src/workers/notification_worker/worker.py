from arq.connections import RedisSettings
from loguru import logger as log

from src.shared.core.logger import setup_logging
from src.workers.core.base import BaseArqSettings, base_shutdown, base_startup
from src.workers.core.config import WorkerSettings as CoreWorkerSettings

from .dependencies import SHUTDOWN_DEPENDENCIES, STARTUP_DEPENDENCIES
from .tasks.task_aggregator import FUNCTIONS

# Инициализируем настройки воркера
settings = CoreWorkerSettings()


async def worker_startup(ctx: dict) -> None:
    """
    Инициализация воркера уведомлений.
    """
    # Инициализируем логирование для этого воркера
    setup_logging(settings, "notification_worker")

    await base_startup(ctx)

    log.info("NotificationWorkerStartup | Initializing dependencies.")
    for dependency_func in STARTUP_DEPENDENCIES:
        await dependency_func(ctx, settings)
    log.info("NotificationWorkerStartup | All dependencies initialized.")


async def worker_shutdown(ctx: dict) -> None:
    """
    Очистка ресурсов воркера уведомлений.
    """
    log.info("NotificationWorkerShutdown | Shutting down dependencies.")
    for dependency_func in SHUTDOWN_DEPENDENCIES:
        await dependency_func(ctx, settings)
    log.info("NotificationWorkerShutdown | All dependencies shut down.")

    await base_shutdown(ctx)


class WorkerSettings(BaseArqSettings):
    """
    Настройки ARQ воркера для уведомлений.
    """

    # Используем умное определение хоста Redis
    redis_settings = RedisSettings(
        host=settings.effective_redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        database=0,
    )

    # Используем настройки из WorkerSettings для конфигурации ARQ
    max_jobs = settings.arq_max_jobs
    job_timeout = settings.arq_job_timeout
    keep_result = settings.arq_keep_result

    on_startup = worker_startup
    on_shutdown = worker_shutdown

    # Регистрация задач
    functions = FUNCTIONS
