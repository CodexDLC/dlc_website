"""
Shared Installer — noop.

Shared core (src/shared/) всегда включён. Installer ничего не делает.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.init_project.installers.base import BaseInstaller

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class SharedInstaller(BaseInstaller):
    name = "Shared Core"

    def install(self, ctx: InstallContext) -> None:
        """Shared всегда включён — ничего не делаем."""
