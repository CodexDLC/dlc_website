from aiogram.types import InlineKeyboardMarkup
from pydantic import BaseModel, ConfigDict


class ViewResultDTO(BaseModel):
    """
    DTO для представления одного сообщения (текст + клавиатура).
    """

    text: str
    kb: InlineKeyboardMarkup | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MessageCoordsDTO(BaseModel):
    """
    Координаты сообщения в Telegram.
    """

    chat_id: int
    message_id: int


class UnifiedViewDTO(BaseModel):
    """
    Единый DTO ответа от Оркестратора.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    clean_history: bool = False
    alert_text: str | None = None

    # ID сообщения, которое вызвало действие (например, /start), чтобы его удалить
    trigger_message_id: int | None = None

    # --- Routing & Session ---
    chat_id: int | str | None = None
    session_key: int | str | None = None
    mode: str | None = None
    message_thread_id: int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MenuViewDTO(BaseModel):
    text: str
    keyboard: InlineKeyboardMarkup | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
