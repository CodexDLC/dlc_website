from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile static assets (CSS/JS) from compiler_config.json files."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n--- Compiling Static Assets ---"))

        try:
            from codex_core.dev.static_compiler import StaticCompiler
        except ImportError:
            self.stdout.write(
                self.style.WARNING("  Warning: codex-core (StaticCompiler) not found. Skipping compilation.")
            )
            return

        compiler = StaticCompiler()
        search_dirs: list[Path] = [Path(d) for d in getattr(settings, "STATICFILES_DIRS", [])]

        for app_config in apps.get_app_configs():
            app_static = Path(app_config.path) / "static"
            if app_static.exists():
                search_dirs.append(app_static)

        compiled_any = False
        for sdir_path in search_dirs:
            for config_path in sdir_path.rglob("compiler_config.json"):
                compiled_any = True
                self.stdout.write(f"  Compiling from: {config_path}")
                compiler.compile_from_config(config_path)

        if not compiled_any:
            self.stdout.write("  No compiler_config.json files found.")

        self.stdout.write(self.style.SUCCESS("--- Static Assets Ready ---\n"))
