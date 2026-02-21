from aiogram.types import CallbackQuery, Message

from src.telegram_bot.features.telegram.notifications.resources.callbacks import NotificationsCallback
from src.telegram_bot.features.telegram.notifications.resources.dto import QueryContext
from src.telegram_bot.services.helper.context_helper import ContextHelper


def extract_context(call: CallbackQuery, callback_data: NotificationsCallback) -> QueryContext:
    """
    Извлекает контекст для уведомлений, используя базовый хелпер.
    """
    # 1. Используем глобальный хелпер для базовых полей
    base_ctx = ContextHelper.extract_base_context(call)

    # 2. Достаем специфичные для уведомлений данные
    message_text = None
    if isinstance(call.message, Message):
        message_text = call.message.text

    # 3. Собираем итоговый QueryContext
    return QueryContext(
        **base_ctx.model_dump(),
        action=callback_data.action,
        session_id=callback_data.session_id,
        message_text=message_text,
    )
