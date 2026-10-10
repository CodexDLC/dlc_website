from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        """
        Initialize logging when Django starts.
        Uses codex-core standards if available, with a standard fallback.
        """
        from .logger import init_logging

        init_logging()
