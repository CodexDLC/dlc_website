"""
Interactive management menu for Django projects.

Usage:
    python manage.py menu
"""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

import questionary
from django.core.management import BaseCommand, call_command
from rich.console import Console

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[4]
MANAGE_PY = PROJECT_ROOT / "manage.py"


def _run_blocking(command: str) -> None:
    """Run a blocking Django command via subprocess."""
    subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, str(MANAGE_PY), command],
        check=False,
        cwd=PROJECT_ROOT,
    )


SECTIONS: dict[str, dict[str, object]] = {
    "▶ Start / Build": {
        "startserver": lambda: _run_blocking("startserver"),
        "compile_assets": lambda: call_command("compile_assets"),
        "collectstatic": lambda: call_command("collectstatic", interactive=False),
    },
    "🗄️ Migrations": {
        "makemigrations": lambda: call_command("makemigrations"),
        "migrate": lambda: call_command("migrate"),
        "showmigrations": lambda: call_command("showmigrations"),
        "sqlmigrate": lambda: console.print("Usage: python manage.py sqlmigrate <app> <migration>", style="yellow"),
    },
    "🌍 Translations": {
        "codex_makemessages": lambda: call_command("codex_makemessages"),
        "compilemessages": lambda: call_command("compilemessages"),
    },
    "⚙️ Content": {
        "update_site_settings": lambda: call_command("update_site_settings"),
        "update_all_content": lambda: call_command("update_all_content"),
    },
    "🧰 Utilities": {
        "check": lambda: call_command("check"),
        "shell": lambda: _run_blocking("shell"),
    },
}


class Command(BaseCommand):
    help = "Interactive management menu"

    def handle(self, *args: object, **options: object) -> None:
        while True:
            category = questionary.select(
                "Project Menu — runtime commands for this Django project:",
                choices=[*list(SECTIONS.keys()), "❌ Exit"],
            ).ask()

            if not category or category == "❌ Exit":
                break

            ops = SECTIONS[category]
            op = questionary.select(
                f"{category} — select action:",
                choices=[*list(ops.keys()), "← Back"],
            ).ask()

            if not op or op == "← Back":
                continue

            console.print(f"\n[bold cyan]▶ Running:[/bold cyan] {op}\n")
            try:
                ops[op]()  # type: ignore[operator]
            except SystemExit:
                pass
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")

            console.print()
