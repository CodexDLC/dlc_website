from src.telegram_bot.services.base import ViewResultDTO

from ..resources.dto import EventNotificationPayload
from ..resources.formatters import format_notification_message
from ..resources.keyboards import build_main_kb


class NotificationsUI:
    """
    UI сервис для фичи Notifications.
    """

    def render_notification(self, payload: EventNotificationPayload, topic_id: int | None = None) -> ViewResultDTO:
        text = format_notification_message(payload)
        kb = build_main_kb(payload.entity_id or "unknown", topic_id=topic_id)

        return ViewResultDTO(text=text, kb=kb)
