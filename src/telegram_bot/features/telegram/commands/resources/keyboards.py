"""
Клавиатуры для фичи commands.
"""

from typing import cast

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext

from src.telegram_bot.features.telegram.bot_menu.resources.callbacks import DashboardCallback


def build_welcome_keyboard(is_admin: bool = False):
    """
    Клавиатура приветственного экрана.
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n.welcome.btn.launch(), callback_data=DashboardCallback(action="select", target="bot_menu").pack()
    )

    if is_admin:
        builder.button(
            text=i18n.welcome.btn.admin(),
            callback_data=DashboardCallback(action="select", target="dashboard_admin").pack(),
        )

    builder.adjust(1)
    return builder.as_markup()
