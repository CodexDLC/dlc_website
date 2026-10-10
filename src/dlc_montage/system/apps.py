from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "system"
    label = "system"
    verbose_name = _("Система")
