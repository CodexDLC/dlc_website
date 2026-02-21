from src.shared.core.logger import setup_logging as _setup_logging

from .config import settings

# Экспортируем функцию настройки, но уже с привязанными параметрами (частично)
# или просто вызываем её в main.py


def setup_loguru() -> None:
    """
    Configures Loguru logger using shared implementation.
    """
    _setup_logging(settings, service_name="backend")
