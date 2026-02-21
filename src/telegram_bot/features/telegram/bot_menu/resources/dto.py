from src.telegram_bot.services.base.context_dto import BaseBotContext


class MenuContext(BaseBotContext):
    """
    Контекст специфичный для фичи bot_menu.
    """

    action: str
    target: str | None = None
