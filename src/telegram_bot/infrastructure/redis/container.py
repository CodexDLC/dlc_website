from redis.asyncio import Redis

from src.shared.core.redis_service import RedisService
from src.telegram_bot.infrastructure.redis.managers.notifications.appointment_cache import AppointmentCacheManager
from src.telegram_bot.infrastructure.redis.managers.sender.sender_manager import SenderManager


class RedisContainer:
    """
    Контейнер для всех Redis-менеджеров.
    Обеспечивает единую точку доступа к слою данных Redis.
    """

    def __init__(self, redis_client: Redis):
        """
        Инициализирует контейнер с менеджерами.

        Args:
            redis_client: Экземпляр клиента Redis.
        """
        # 1. Base Service (Wrapper)
        self.service = RedisService(redis_client)

        # 2. Managers
        # Менеджер для управления координатами UI (Sender)
        self.sender = SenderManager(self.service)

        # Менеджер для кэширования данных заявок
        self.appointment_cache = AppointmentCacheManager(self.service)
