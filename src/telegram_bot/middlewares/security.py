from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from loguru import logger as log

from src.telegram_bot.core.container import BotContainer

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext


class SecurityMiddleware(BaseMiddleware):
    """
    Middleware для защиты от подмены данных пользователя.
    Проверяет что user_id из события совпадает с user_id в FSM State.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("user")
        state: FSMContext | None = data.get("state")

        # Если нет user или state - пропускаем проверку
        if not user or not state:
            return await handler(event, data)

        # Получаем session_data из FSM
        state_data = await state.get_data()
        session_data = state_data.get("session_data", {})
        stored_user_id = session_data.get("user_id")

        # Если в сессии есть user_id, проверяем совпадение
        if stored_user_id and stored_user_id != user.id:
            log.error(
                f"Security: user_id mismatch! "
                f"event_user={user.id} stored_user={stored_user_id} | "
                f"Possible session hijacking attempt"
            )

            # Блокируем запрос и уведомляем пользователя
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Ошибка безопасности. Сессия не принадлежит вам.", show_alert=True)

            return None  # Прерываем обработку

        # Всё ок, пропускаем дальше
        return await handler(event, data)


def setup(container: BotContainer) -> BaseMiddleware:
    """Фабрика для создания middleware."""
    return SecurityMiddleware()
