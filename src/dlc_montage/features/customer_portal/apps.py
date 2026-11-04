"""Регистрация клиентского кабинета."""

from django.apps import AppConfig


class CustomerPortalConfig(AppConfig):
    """Владение клиентскими правами, заявками и проверкой работ."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "features.customer_portal"

    def ready(self):
        from . import email_access_signals  # noqa: F401
