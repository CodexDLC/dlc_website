"""
UI для фичи commands.
"""

from typing import cast

from aiogram_i18n import I18nContext

from src.telegram_bot.features.telegram.commands.resources.keyboards import build_welcome_keyboard
from src.telegram_bot.services.base.view_dto import ViewResultDTO


class CommandsUI:
    """
    Класс для рендеринга интерфейса команд.
    """

    def render_welcome_screen(self, name: str, is_admin: bool = False) -> ViewResultDTO:
        """
        Рендерит приветственный экран.
        """
        i18n = cast("I18nContext", I18nContext.get_current())

        # Используем тернарный оператор по рекомендации Ruff
        text = i18n.welcome.admin(name=name) if is_admin else i18n.welcome.user(name=name)

        keyboard = build_welcome_keyboard(is_admin=is_admin)

        return ViewResultDTO(text=text, kb=keyboard)
