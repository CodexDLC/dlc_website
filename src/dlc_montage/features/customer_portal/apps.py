"""Регистрация клиентского кабинета."""

from django.apps import AppConfig


class CustomerPortalConfig(AppConfig):
    """Владение клиентскими правами, заявками и проверкой работ."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "features.customer_portal"
