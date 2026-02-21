from typing import Any

from .texts import NotificationsTexts


class NotificationsFormatter:
    """
    Форматирование данных для фичи Notifications.
    """

    def format_main(self, payload: Any) -> str:
        return f"{NotificationsTexts.title()}\n\n{NotificationsTexts.description()}"

    def prepare_email_data(
        self, appointment_data: dict[str, Any], status: str, reason_text: str | None = None
    ) -> dict[str, Any]:
        """
        Формирует плоский словарь данных для Email-шаблона.
        """
        if status == "confirmed":
            email_tag = NotificationsTexts.EMAIL_CONFIRM_TAG
            email_subject = NotificationsTexts.EMAIL_CONFIRM_SUBJECT
            email_body = NotificationsTexts.EMAIL_CONFIRM_BODY
        else:
            email_tag = NotificationsTexts.EMAIL_CANCEL_TAG
            email_subject = NotificationsTexts.EMAIL_CANCEL_SUBJECT
            email_body = NotificationsTexts.EMAIL_CANCEL_BODY

        first_name = appointment_data.get("first_name", "Kunde")
        last_name = appointment_data.get("last_name", "")
        visits_count = appointment_data.get("visits_count", 0)
        greeting = NotificationsTexts.get_email_greeting(first_name, last_name, visits_count)

        dt_str = appointment_data.get("datetime", "")
        date_part = dt_str.split(" ")[0] if " " in dt_str else dt_str
        time_part = dt_str.split(" ")[1] if " " in dt_str else ""

        return {
            "email_tag": email_tag,
            "email_subject": email_subject,
            "email_body": email_body,
            "greeting": greeting,
            "service_name": appointment_data.get("service_name"),
            "date": date_part,
            "time": time_part,
            "duration_minutes": appointment_data.get("duration_minutes", 30),
            "cancellation_reason": reason_text,
            "status": status,
        }
