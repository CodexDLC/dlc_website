from typing import cast

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext

from .callbacks import NotificationsCallback


def build_main_kb(entity_id: int | str, topic_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Keyboard for managing an event notification (Approve / Reject).

    Args:
        entity_id: domain entity ID
        topic_id: Telegram topic ID (for editing messages in topics/threads)
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    builder.button(
        text=i18n.notifications.btn.approve(),
        callback_data=NotificationsCallback(action="approve", session_id=entity_id, topic_id=topic_id).pack(),
    )
    builder.button(
        text=i18n.notifications.btn.reject(),
        callback_data=NotificationsCallback(action="reject", session_id=entity_id, topic_id=topic_id).pack(),
    )

    builder.adjust(2)
    return builder.as_markup()


def build_reject_reasons_kb(entity_id: int | str, topic_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Keyboard with rejection reason buttons.
    TODO: Add your domain-specific rejection reasons.
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    builder = InlineKeyboardBuilder()

    # TODO: Add your domain-specific rejection reasons here
    # Each reason maps to a callback action like "reject_busy", "reject_other"
    reject_reasons = [
        ("reject_busy", i18n.notifications.reason.busy()),
        ("reject_other", i18n.notifications.reason.other()),
    ]

    for action, label in reject_reasons:
        builder.button(
            text=label,
            callback_data=NotificationsCallback(action=action, session_id=entity_id, topic_id=topic_id).pack(),
        )

    builder.button(
        text=i18n.notifications.alert.cancelled(),
        callback_data=NotificationsCallback(action="cancel_reject", session_id=entity_id, topic_id=topic_id).pack(),
    )

    builder.adjust(1)
    return builder.as_markup()
