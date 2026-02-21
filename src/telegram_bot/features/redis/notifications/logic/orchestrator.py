from typing import Any

from loguru import logger as log

from src.telegram_bot.core.config import BotSettings
from src.telegram_bot.services.base import UnifiedViewDTO, ViewResultDTO

from ..resources.dto import EventNotificationPayload
from ..ui.ui import NotificationsUI


class NotificationsOrchestrator:
    """
    Оркестратор для фичи Notifications.
    """

    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.ui = NotificationsUI()

    def handle_notification(self, raw_payload: dict[str, Any]) -> UnifiedViewDTO:
        """
        Обрабатывает входящее уведомление, валидируя его через Pydantic.
        """
        log.debug(f"NotificationsOrchestrator | Validating payload: {raw_payload}")

        try:
            payload = EventNotificationPayload(**raw_payload)
        except Exception as e:
            log.error(f"NotificationsOrchestrator | Validation error: {e}")
            return self.handle_failure(raw_payload, str(e))

        target_chat_id = self.settings.telegram_admin_channel_id
        message_thread_id = self.settings.telegram_notification_topic_id

        # TODO: Map domain-specific fields to topics if needed
        # Example:
        #   if payload.extra.get("category") and self.settings.telegram_topics:
        #       topic_id = self.settings.telegram_topics.get(payload.extra["category"])
        #       if topic_id:
        #           message_thread_id = topic_id

        view_result = self.ui.render_notification(payload, topic_id=message_thread_id)

        session_key = str(payload.entity_id) if payload.entity_id is not None else payload.event_type

        return UnifiedViewDTO(
            content=view_result,
            chat_id=target_chat_id,
            session_key=session_key,
            mode="topic" if message_thread_id else "channel",
            message_thread_id=message_thread_id,
        )

    def handle_failure(self, raw_payload: dict[str, Any], error_msg: str) -> UnifiedViewDTO:
        entity_id = raw_payload.get("entity_id", raw_payload.get("id", "???"))
        text = (
            f"⚠️ <b>Ошибка обработки уведомления</b>\n\n"
            f"Поступило событие <b>#{entity_id}</b>, но бот не смог обработать данные.\n"
            f"<b>Ошибка:</b> <code>{error_msg}</code>"
        )
        return UnifiedViewDTO(
            content=ViewResultDTO(text=text),
            chat_id=self.settings.telegram_admin_channel_id,
            session_key=f"fail_{entity_id}",
            mode="topic",
            message_thread_id=self.settings.telegram_notification_topic_id,
        )
