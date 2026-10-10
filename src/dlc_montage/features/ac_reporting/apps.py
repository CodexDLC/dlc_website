from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcReportingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "features.ac_reporting"
    verbose_name = _("AC reporting")
