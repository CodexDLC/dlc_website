from typing import Any

from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    help = "Start the development server after compiling static assets."

    def handle(self, *args: Any, **options: Any) -> None:
        import os
        from django.core.management import call_command

        # Django autoreloader spawns two processes; compile only in the outer one
        if os.environ.get("RUN_MAIN") != "true":
            call_command("compile_assets")

        super().handle(*args, **options)
