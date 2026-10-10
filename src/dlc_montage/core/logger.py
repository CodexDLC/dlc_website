import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Union

from django.conf import settings

if TYPE_CHECKING:
    from loguru import Logger

# Declare logger with a Union type to satisfy mypy
logger: Union[logging.Logger, "Logger"]

try:
    from codex_core.common.loguru_setup import setup_logging
    from loguru import logger as loguru_logger

    logger = loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    LOGURU_AVAILABLE = False


class DjangoLoggingSettingsAdapter:
    """Adapts Django settings to codex-core LoggingSettingsProtocol."""

    def __init__(self) -> None:
        self.log_level_console = getattr(settings, "LOG_LEVEL_CONSOLE", "INFO")
        self.log_level_file = getattr(settings, "LOG_LEVEL_FILE", "DEBUG")
        self.log_rotation = getattr(settings, "LOG_ROTATION", "10 MB")
        self.debug = getattr(settings, "DEBUG", False) and getattr(settings, "LOG_FILE_ENABLED", True)
        base_log_dir = Path(getattr(settings, "LOG_DIR", "logs"))
        self.log_dir = str(base_log_dir / f"process-{os.getpid()}") if self.debug else str(base_log_dir)


def init_logging() -> None:
    """Initialize logging based on project settings and available libraries."""
    if not LOGURU_AVAILABLE:
        # Fallback to standard Django LOGGING already configured in settings
        if isinstance(logger, logging.Logger):
            logger.info("Loguru or codex-core not found. Using standard Django logging.")
        return

    # Use codex-core setup
    service_name = getattr(settings, "PROJECT_NAME", "django-backend")
    adapter = DjangoLoggingSettingsAdapter()

    setup_logging(
        settings=adapter,
        service_name=service_name,
        intercept_loggers=["django", "django.server", "django.db.backends"],
        log_levels={
            "django.db.backends": logging.WARNING,
            "django.utils.autoreload": logging.WARNING,
            "django_lifecycle": logging.WARNING,
        },
    )

    if not isinstance(logger, logging.Logger):
        logger.info(f"Loguru initialized via codex-core for {service_name}")
