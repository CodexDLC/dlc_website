from pydantic import BaseModel, ConfigDict


class BaseBotContext(BaseModel):
    """
    Базовый контекст события Telegram.
    Содержит минимально необходимый набор данных для работы любого оркестратора.
    """

    user_id: int
    chat_id: int
    message_id: int | None = None
    message_thread_id: int | None = None

    @property
    def session_key(self) -> int:
        """Ключ для хранения состояния в Redis (по умолчанию user_id)."""
        return self.user_id

    model_config = ConfigDict(from_attributes=True)
