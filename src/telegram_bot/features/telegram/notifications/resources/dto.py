from src.telegram_bot.services.base.context_dto import BaseBotContext


class QueryContext(BaseBotContext):
    """
    Pydantic-модель для хранения извлеченной информации из CallbackQuery.
    Наследуется от базового контекста бота.
    """

    action: str
    session_id: int | str | None = None
    message_text: str | None = None
