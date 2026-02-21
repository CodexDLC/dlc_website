"""
Renamer Action — замена имени проекта в файлах.

Ищет маркер PROJECT_NAME_MARKER ("project-template") и заменяет
на выбранное пользователем имя проекта.
"""

from __future__ import annotations

from tools.init_project.config import (
    PROJECT_NAME_MARKER,
    RENAME_TARGETS,
    InstallContext,
)


class RenamerAction:
    """Заменяет имя проекта в целевых файлах."""

    def execute(self, ctx: InstallContext) -> None:
        if ctx.project_name == PROJECT_NAME_MARKER:
            print("    ⏭️  Project name unchanged — skipping rename")
            return

        for rel_path in RENAME_TARGETS:
            file_path = ctx.project_root / rel_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            if PROJECT_NAME_MARKER not in content:
                continue

            new_content = content.replace(PROJECT_NAME_MARKER, ctx.project_name)
            file_path.write_text(new_content, encoding="utf-8")
            print(f"    ✏️  Renamed in: {rel_path}")
