from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger as log

from src.telegram_bot.core.container import BotContainer


class UserValidationMiddleware(BaseMiddleware):
    """
    Middleware для валидации наличия пользователя в событии.
    Блокирует обработку событий без user (защита от ботов/системных событий).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None

        # Проверяем только входящие события от пользователей
        if isinstance(event, Message | CallbackQuery):
            user = event.from_user

            # Если входящее событие БЕЗ пользователя - блокируем (защита)
            if not user:
                log.warning(
                    f"UserValidation: Incoming event without user, skipping | event_type={type(event).__name__}"
                )
                return None  # Прерываем обработку

            # Добавляем user в контекст (чтобы не извлекать повторно в хендлерах)
            data["user"] = user

        # Для остальных типов событий (Update, etc.) - пропускаем без проверки
        # Это позволяет боту отправлять сообщения в каналы
        return await handler(event, data)


def setup(container: BotContainer) -> BaseMiddleware:
    """Фабрика для создания middleware."""
    return UserValidationMiddleware()
