from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TelegramAccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "features.telegram_access"
    verbose_name = _("Telegram access")
