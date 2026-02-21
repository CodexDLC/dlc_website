"""
Poetry Action — управление зависимостями в pyproject.toml.

Удаляет optional-dependency группы для невыбранных модулей.
Например, если нет бота — удаляет секцию [project.optional-dependencies].bot.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class PoetryAction:
    """Удаляет ненужные группы зависимостей из pyproject.toml."""

    def execute(self, ctx: InstallContext) -> None:
        pyproject_path = ctx.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            print("    ⚠️  pyproject.toml not found — skipping")
            return

        content = pyproject_path.read_text(encoding="utf-8")
        groups_to_remove: list[str] = []

        if ctx.backend != "fastapi":
            groups_to_remove.append("fastapi")
        if ctx.backend != "django":
            groups_to_remove.append("django")
        if not ctx.include_bot:
            groups_to_remove.append("bot")

        if not groups_to_remove:
            print("    ⏭️  All dependency groups needed — skipping")
            return

        for group in groups_to_remove:
            content = self._remove_optional_group(content, group)
            print(f"    🗑️  Removed dependency group: {group}")

        pyproject_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _remove_optional_group(content: str, group_name: str) -> str:
        """Удаляет optional-dependency группу из pyproject.toml.

        Ищет блок вида:
            # Comment (optional)
            group_name = [
                "dep1",
                "dep2",
            ]
        И удаляет его целиком.
        """
        # Паттерн: опциональный комментарий + имя группы + массив
        pattern = re.compile(
            r"(?:^# [^\n]*\n)?"  # опциональная строка-комментарий
            rf"^{re.escape(group_name)}\s*=\s*\[\s*\n"  # group = [
            r"(?:.*\n)*?"  # содержимое массива
            r"^\]\s*\n?",  # ]
            re.MULTILINE,
        )
        return pattern.sub("", content)
