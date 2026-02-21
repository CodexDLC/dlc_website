"""
Bot Installer — noop.

Telegram Bot уже готов в шаблоне. Installer просто оставляет код как есть.
В будущем может добавлять конфигурации (с/без worker, с/без RBAC).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.init_project.installers.base import BaseInstaller

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class BotInstaller(BaseInstaller):
    name = "Telegram Bot"

    def install(self, ctx: InstallContext) -> None:
        """Telegram Bot уже в шаблоне — ничего не делаем."""
