from typing import cast

from aiogram_i18n import I18nContext


class NotificationsTexts:
    """
    Text wrappers for the Telegram Notifications feature.
    Telegram-visible texts are served via i18n FTL files.
    Email texts below are template stubs — TODO: replace with your project texts.
    """

    @staticmethod
    def get_i18n():
        return cast("I18nContext", I18nContext.get_current())

    # === Telegram texts (via i18n) ===
    @classmethod
    def title(cls):
        return cls.get_i18n().notifications.title()

    @classmethod
    def description(cls):
        return cls.get_i18n().notifications.description()

    @classmethod
    def status_approved(cls):
        return cls.get_i18n().notifications.status.approved()

    @classmethod
    def status_rejected(cls):
        return cls.get_i18n().notifications.status.rejected()

    @classmethod
    def prompt_select_reason(cls):
        return cls.get_i18n().notifications.prompt.select.reason()

    @classmethod
    def alert_approved(cls):
        return cls.get_i18n().notifications.alert.approved()

    @classmethod
    def alert_rejected(cls):
        return cls.get_i18n().notifications.alert.rejected()

    @classmethod
    def alert_cancelled(cls):
        return cls.get_i18n().notifications.alert.cancelled()

    @classmethod
    def alert_deleted(cls):
        return cls.get_i18n().notifications.alert.deleted()

    @classmethod
    def error_api(cls):
        return cls.get_i18n().notifications.error.api()

    # === Email texts (stubs — not via i18n, used for backend email sending) ===
    # TODO: Replace with your project email subjects and bodies
    EMAIL_REJECT_REASON_BUSY = "The requested time slot is no longer available."
    EMAIL_REJECT_REASON_OTHER = "We are unable to accommodate your request at this time."

    # TODO: Replace with your email confirmation subject/body
    EMAIL_CONFIRM_TAG = "CONFIRMATION"
    EMAIL_CONFIRM_SUBJECT = "Appointment Confirmed"
    EMAIL_CONFIRM_BODY = "Your request has been confirmed. We look forward to seeing you."

    # TODO: Replace with your email cancellation subject/body
    EMAIL_CANCEL_TAG = "CANCELLATION"
    EMAIL_CANCEL_SUBJECT = "Appointment Cancelled"
    EMAIL_CANCEL_BODY = "Unfortunately, we have to cancel your appointment. We apologize for the inconvenience."

    @staticmethod
    def get_email_greeting(first_name: str, last_name: str, visits_count: int | str) -> str:
        """
        Returns a greeting string for email messages.
        TODO: Customize greeting logic for your project.
        """
        try:
            v_count = int(visits_count)
        except (ValueError, TypeError):
            v_count = 0

        full_name = f"{first_name} {last_name}".strip()
        if v_count == 0:
            return f"Dear {full_name},"
        elif 1 <= v_count <= 4:
            return f"Hello {first_name},"
        else:
            return f"Hi {first_name},"
