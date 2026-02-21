"""
Клавиатуры для фичи bot_menu.
"""

from typing import cast

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext

from src.telegram_bot.features.telegram.bot_menu.resources.callbacks import DashboardCallback


def build_dashboard_keyboard(buttons: dict, mode: str = "bot_menu"):
    """
    Собирает клавиатуру дашборда.
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    # 1. Сортируем кнопки фич по приоритету
    sorted_buttons = sorted(buttons.values(), key=lambda x: x.get("priority", 100))

    # 2. Добавляем кнопки фич
    for btn_data in sorted_buttons:
        icon = btn_data.get("icon", "")
        label = btn_data.get("text", "Feature")
        text = f"{icon} {label}".strip()
        key = btn_data.get("key")

        callback = DashboardCallback(action="select", target=key).pack()
        builder.button(text=text, callback_data=callback)

    builder.adjust(2)

    # 3. Добавляем системные кнопки
    if mode == "dashboard_admin":
        builder.row()
        builder.button(
            text=i18n.menu.btn.back.to.user(),
            callback_data=DashboardCallback(action="select", target="bot_menu").pack(),
        )

    return builder.as_markup()
