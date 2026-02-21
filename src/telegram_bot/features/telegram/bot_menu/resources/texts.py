"""
Тексты для фичи bot_menu.
"""

from typing import cast

from aiogram_i18n import I18nContext


def get_dashboard_title(mode: str = "bot_menu") -> str:
    """Возвращает заголовок в зависимости от режима."""
    i18n = cast("I18nContext", I18nContext.get_current())

    if mode == "dashboard_admin":
        return i18n.menu.admin.title()
    return i18n.menu.dashboard.title()
