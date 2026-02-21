from __future__ import annotations

from typing import TYPE_CHECKING, cast

from aiogram_i18n import I18nContext

if TYPE_CHECKING:
    from src.shared.schemas.stream.notification import NotificationPayload


def format_notification_message(payload: NotificationPayload) -> str:
    """
    Форматирует сообщение уведомления на основе данных из Redis Stream.
    Использует i18n для локализации.
    """
    i18n = cast("I18nContext", I18nContext.get_current())
    lines = []

    # Title / Event Type
    if payload.event_type == "system":
        lines.append(i18n.notifications.system.event())
    elif payload.event_type == "user":
        lines.append(i18n.notifications.user.event())
    else:
        lines.append(i18n.notifications.new.event())

    # Entity ID
    if payload.entity_id is not None:
        lines.append(i18n.notifications.entity.id(entity_id=payload.entity_id))

    # Description
    if payload.description:
        lines.append(i18n.notifications.event.description(description=payload.description))

    # TODO: Add formatting for your domain-specific fields from payload.extra
    # Example:
    #   if payload.extra.get("amount"):
    #       lines.append(f"Amount: {payload.extra['amount']}")

    return "\n".join(lines)
