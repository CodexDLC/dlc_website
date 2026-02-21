from typing import cast

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext

from .callbacks import NotificationsCallback


def build_main_kb(appointment_id: int, topic_id: int | None = None):
    """
    Клавиатура управления заявкой (Подтвердить / Отклонить).
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n.common.btn.confirm(),
        callback_data=NotificationsCallback(action="approve", session_id=appointment_id, topic_id=topic_id).pack(),
    )
    builder.button(
        text=i18n.common.btn.cancel(),  # Используем общее "Отмена" для отклонения
        callback_data=NotificationsCallback(action="reject", session_id=appointment_id, topic_id=topic_id).pack(),
    )

    builder.adjust(2)
    return builder.as_markup()


def build_reject_reasons_kb(appointment_id: int, topic_id: int | None = None):
    """
    Клавиатура с причинами отклонения.
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    reasons = [
        ("reject_busy", i18n.notifications.reason.busy()),
        ("reject_ill", i18n.notifications.reason.ill()),
        ("reject_materials", i18n.notifications.reason.materials()),
        ("reject_blacklist", i18n.notifications.reason.blacklist()),
    ]

    for action, text in reasons:
        builder.button(
            text=text,
            callback_data=NotificationsCallback(action=action, session_id=appointment_id, topic_id=topic_id).pack(),
        )

    builder.button(
        text=i18n.common.btn.back(),
        callback_data=NotificationsCallback(
            action="cancel_reject", session_id=appointment_id, topic_id=topic_id
        ).pack(),
    )

    builder.adjust(1)
    return builder.as_markup()


def build_post_action_kb(appointment_id: int, topic_id: int | None = None):
    """
    Клавиатура после обработки (кнопка удаления).
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n.notifications.btn.delete(),
        callback_data=NotificationsCallback(
            action="delete_notification", session_id=appointment_id, topic_id=topic_id
        ).pack(),
    )
    return builder.as_markup()
