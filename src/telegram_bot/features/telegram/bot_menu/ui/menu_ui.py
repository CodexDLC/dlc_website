"""
UI для фичи bot_menu.
"""

from src.telegram_bot.features.telegram.bot_menu.resources.keyboards import build_dashboard_keyboard
from src.telegram_bot.features.telegram.bot_menu.resources.texts import get_dashboard_title
from src.telegram_bot.services.base.view_dto import ViewResultDTO


class BotMenuUI:
    """
    Отвечает за рендеринг главного меню (Дашборда).
    """

    def render_dashboard(self, buttons: dict, mode: str = "bot_menu") -> ViewResultDTO:
        """
        Генерирует ViewResultDTO.
        Вся логика сборки вынесена в ресурсы.
        """
        return ViewResultDTO(text=get_dashboard_title(mode), kb=build_dashboard_keyboard(buttons, mode))
