from typing import Any

from src.telegram_bot.features.telegram.notifications.resources.formatters import NotificationsFormatter
from src.telegram_bot.features.telegram.notifications.resources.keyboards import (
    build_main_kb,
    build_post_action_kb,
    build_reject_reasons_kb,
)
from src.telegram_bot.features.telegram.notifications.resources.texts import NotificationsTexts
from src.telegram_bot.services.base.view_dto import ViewResultDTO


class NotificationsUI:
    """
    UI сервис для фичи Notifications.
    """

    def __init__(self):
        self.formatter = NotificationsFormatter()

    def render_main(self, text: str, appointment_id: int, topic_id: int | None = None) -> ViewResultDTO:
        """Отрисовка основного экрана управления."""
        kb = build_main_kb(appointment_id=appointment_id, topic_id=topic_id)
        return ViewResultDTO(text=text, kb=kb)

    def render_reject_reasons(self, appointment_id: int, topic_id: int | None = None) -> ViewResultDTO:
        """Отрисовка меню выбора причин отклонения."""
        return ViewResultDTO(
            text=NotificationsTexts.prompt_select_reason(),
            kb=build_reject_reasons_kb(appointment_id=appointment_id, topic_id=topic_id),
        )

    def render_post_action(self, text: str, appointment_id: int, topic_id: int | None = None) -> ViewResultDTO:
        """Отрисовка экрана после выполнения действия."""
        kb = build_post_action_kb(appointment_id=appointment_id, topic_id=topic_id)
        return ViewResultDTO(text=text, kb=kb)

    def render_email_data(
        self, appointment_data: dict[str, Any], status: str, reason_text: str | None = None
    ) -> dict[str, Any]:
        """Формирование данных для Email."""
        return self.formatter.prepare_email_data(appointment_data, status, reason_text)
