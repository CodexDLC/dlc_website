from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger as log
from redis.asyncio import Redis

from src.telegram_bot.core.container import BotContainer


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама (Rate Limiting).
    Блокирует частые запросы от одного пользователя через Redis.
    """

    def __init__(self, redis: Redis, rate_limit: float = 1.0):
        """
        Args:
            redis: Redis клиент для хранения ключей троттлинга
            rate_limit: Минимальный интервал между запросами в секундах
        """
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None

        # Получаем user_id из события
        if isinstance(event, Message | CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if not user_id:
            # Если нет user_id, пропускаем (например, системные события)
            return await handler(event, data)

        # Ключ для троттлинга
        key = f"throttle:{user_id}"

        # Проверяем наличие ключа в Redis
        if await self.redis.exists(key):
            # Пользователь заблокирован (слишком часто отправляет запросы)
            log.warning(f"Throttling: user {user_id} blocked (rate limit exceeded)")

            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро! Подождите немного.", show_alert=False)

            return None  # Прерываем обработку

        # Устанавливаем ключ с TTL (время жизни = rate_limit)
        await self.redis.set(key, "1", ex=int(self.rate_limit) or 1)

        return await handler(event, data)


def setup(container: BotContainer) -> BaseMiddleware:
    """Фабрика для создания middleware."""
    return ThrottlingMiddleware(redis=container.redis_client, rate_limit=1.0)
