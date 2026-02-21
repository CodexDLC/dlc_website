"""
FastAPI Installer — noop.

FastAPI уже готов в шаблоне. Installer просто оставляет код как есть.
В будущем может добавлять конфигурации (с/без auth, с/без media).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.init_project.installers.base import BaseInstaller

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class FastAPIInstaller(BaseInstaller):
    name = "FastAPI"

    def install(self, ctx: InstallContext) -> None:
        """FastAPI уже в шаблоне — ничего не делаем."""
