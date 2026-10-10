from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InternalTimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "features.internal_time"
    verbose_name = _("Internal time tracking")
