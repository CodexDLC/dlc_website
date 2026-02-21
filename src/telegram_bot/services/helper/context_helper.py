from aiogram.types import CallbackQuery, Message

from src.telegram_bot.services.base.context_dto import BaseBotContext


class ContextHelper:
    """
    Хелпер для извлечения базового контекста из событий Telegram.
    """

    @staticmethod
    def extract_base_context(event: Message | CallbackQuery) -> BaseBotContext:
        """
        Извлекает базовые ID из сообщения или колбека.
        Гарантирует уникальность user_id (использует chat_id как fallback).
        """
        # Базовое определение user_id
        user_id = event.from_user.id if event.from_user else 0
        chat_id = user_id
        message_id = None
        thread_id = None

        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                chat_id = event.message.chat.id
                message_id = event.message.message_id
                thread_id = event.message.message_thread_id
            # Если from_user нет в колбеке (редко, но бывает), используем chat_id
            if user_id == 0:
                user_id = chat_id

        elif isinstance(event, Message):
            chat_id = event.chat.id
            message_id = event.message_id
            thread_id = event.message_thread_id
            # Если from_user нет (например, пост в канале), используем chat_id для уникальности сессии
            if user_id == 0:
                user_id = chat_id

        return BaseBotContext(user_id=user_id, chat_id=chat_id, message_id=message_id, message_thread_id=thread_id)
