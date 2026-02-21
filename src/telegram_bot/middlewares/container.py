from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.telegram_bot.core.container import BotContainer


class ContainerMiddleware(BaseMiddleware):
    """
    Middleware для внедрения BotContainer в обработчики.
    Передаёт HTTP-клиенты для взаимодействия с Backend API.
    """

    def __init__(self, container: BotContainer):
        self.container = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Внедряем контейнер с HTTP-клиентами
        data["container"] = self.container

        return await handler(event, data)


def setup(container: BotContainer) -> BaseMiddleware:
    """Фабрика для создания middleware."""
    return ContainerMiddleware(container=container)
