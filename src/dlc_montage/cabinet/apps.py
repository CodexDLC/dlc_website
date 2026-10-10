from django.apps import AppConfig


class CabinetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cabinet"

    def ready(self) -> None:
        # cabinet.py is auto-discovered by codex_django.cabinet via autodiscover_modules("cabinet").
        # No manual imports needed here.
        pass
