from collections.abc import Awaitable, Callable
from typing import cast

from loguru import logger as log

from src.shared.core.manager_redis.manager import StreamManager
from src.shared.schemas.site_settings import SiteSettingsSchema
from src.workers.core.base_module.dependencies import close_common_dependencies, init_common_dependencies
from src.workers.core.config import WorkerSettings
from src.workers.notification_worker.services.notification_service import NotificationService

# Определяем тип для функций инициализации/очистки зависимостей
DependencyFunction = Callable[[dict, WorkerSettings], Awaitable[None]]


async def init_stream_manager(ctx: dict, settings: WorkerSettings) -> None:
    """
    Инициализация StreamManager, используя уже инициализированный RedisService.
    """
    log.info("Initializing Stream Manager...")
    try:
        redis_service = ctx.get("redis_service")
        if not redis_service:
            raise RuntimeError("RedisService not found in context. Ensure init_common_dependencies is called first.")

        stream_manager = StreamManager(redis_service)
        ctx["stream_manager"] = stream_manager
        log.info("Stream Manager initialized successfully.")
    except Exception as e:
        log.exception(f"Failed to initialize Stream Manager: {e}")
        raise


async def init_notification_service(ctx: dict, settings: WorkerSettings) -> None:
    """
    Инициализация NotificationService с использованием настроек из Redis (Pydantic объект).
    """
    log.info("Initializing NotificationService...")
    try:
        # Получаем объект настроек с типизацией
        # TC006: Используем кавычки для предотвращения проблем с циклическими импортами в cast
        site_settings = cast("SiteSettingsSchema | None", ctx.get("site_settings"))

        if not site_settings:
            log.warning("Site settings object not found in context, using schema defaults.")
            site_settings = SiteSettingsSchema()

        # Собираем адрес из полей схемы настроек
        address_parts = [site_settings.address_street, site_settings.address_locality]
        address = ", ".join(part for part in address_parts if part)

        notification_service = NotificationService(
            templates_dir=str(settings.TEMPLATES_DIR),
            site_url=site_settings.site_base_url,
            logo_url=site_settings.logo_url,
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            smtp_from_email=settings.SMTP_FROM_EMAIL,
            smtp_use_tls=settings.SMTP_USE_TLS,
            url_path_confirm=site_settings.url_path_confirm,
            url_path_cancel=site_settings.url_path_cancel,
            url_path_reschedule=site_settings.url_path_reschedule,
            url_path_contact_form=site_settings.url_path_contact_form,
            address=address,
            company_name=site_settings.company_name,
        )
        ctx["notification_service"] = notification_service
        log.info("NotificationService initialized successfully.")
    except Exception as e:
        log.exception(f"Failed to initialize NotificationService: {e}")
        raise


# Список функций, которые будут выполняться при старте воркера
STARTUP_DEPENDENCIES: list[DependencyFunction] = [
    init_common_dependencies,  # Сначала общие (Redis, SiteSettings)
    init_stream_manager,  # Затем специфичные для воркера
    init_notification_service,
]

# Список функций, которые будут выполняться при остановке воркера
SHUTDOWN_DEPENDENCIES: list[DependencyFunction] = [
    close_common_dependencies,
]
