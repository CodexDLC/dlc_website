"""
Форматеры для фичи commands.
Преобразуют сырые данные в строки для отображения.
"""

from aiogram.types import Message


class MessageInfoFormatter:
    """Форматирует debug-информацию о сообщении."""

    @staticmethod
    def format_chat_ids(m: Message) -> str:
        user_id = m.from_user.id if m.from_user else "N/A"
        chat_id = m.chat.id
        return f"<b>User ID:</b> <code>{user_id}</code>\n<b>Chat ID:</b> <code>{chat_id}</code>"
