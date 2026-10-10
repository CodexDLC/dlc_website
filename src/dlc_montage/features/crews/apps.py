from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CrewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "features.crews"
    verbose_name = _("Crews")
