from typing import Any

from src.telegram_bot.features.redis.errors.ui.error_ui import ErrorUI
from src.telegram_bot.services.base.base_orchestrator import BaseBotOrchestrator
from src.telegram_bot.services.base.view_dto import UnifiedViewDTO


class ErrorOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор для отображения системных ошибок.
    """

    def __init__(self):
        super().__init__(expected_state=None)
        self.ui = ErrorUI()

    async def handle_entry(self, user_id: int, chat_id: int | None = None, payload: Any = None) -> UnifiedViewDTO:
        """
        Точка входа.
        """
        # Если payload содержит текст ошибки, используем его
        error_text = str(payload) if payload else "Unknown system error occurred."
        return await self.render(error_text)

    async def render_content(self, payload: Any) -> Any:
        """
        Рендерит сообщение об ошибке.
        Ожидает словарь для ErrorUI.
        """
        return self.ui.render_error({"error": str(payload)})
