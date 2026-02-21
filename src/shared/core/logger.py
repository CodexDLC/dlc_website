import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.shared.core.config import CommonSettings

if TYPE_CHECKING:
    from types import FrameType


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные сообщения `logging` и направляет их в `loguru`.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Перенаправляет запись лога в loguru."""
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_logging(settings: CommonSettings, service_name: str) -> None:
    """
    Настраивает loguru.

    Args:
        settings: Объект настроек (CommonSettings или наследник).
        service_name: Имя сервиса ('backend' или '02_telegram_bot').
                      Используется для создания подпапки в логах.
    """
    logger.remove()

    # Формируем пути к логам: logs/backend/debug.log или logs/02_telegram_bot/debug.log
    base_log_dir = Path(settings.log_dir) / service_name

    log_file_debug = base_log_dir / "debug.log"
    log_file_errors = base_log_dir / "errors.json"

    # Консольный вывод (общий формат)
    logger.add(
        sink=sys.stdout,
        level=settings.log_level_console.upper(),
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            f"<magenta>{service_name}</magenta> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # Файл debug
    logger.add(
        sink=str(log_file_debug),
        level=settings.log_level_file.upper(),
        rotation=settings.log_rotation,
        compression="zip",
        format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Файл errors (JSON)
    logger.add(
        sink=str(log_file_errors),
        level="ERROR",
        serialize=True,
        rotation=settings.log_rotation,
        compression="zip",
    )

    # Перехват стандартного logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Перехват логов библиотек
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("arq").handlers = [InterceptHandler()]
    logging.getLogger("arq.worker").handlers = [InterceptHandler()]

    # Настройка уровней для библиотек
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)
    logging.getLogger("arq").setLevel(logging.INFO)

    logger.info(f"LoggerSetup | service={service_name} status=success path='{base_log_dir}'")
