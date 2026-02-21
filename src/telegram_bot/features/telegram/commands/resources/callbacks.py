"""
Callback Data для фичи commands.
"""

from aiogram.filters.callback_data import CallbackData


class SystemCallback(CallbackData, prefix="sys"):
    """Глобальный callback для системных действий."""

    action: str  # "logout", "main_menu"


class SettingsCallback(CallbackData, prefix="cmd_settings"):
    """Callback для меню настроек."""

    action: str  # "open", "toggle_notifications", "change_language"
