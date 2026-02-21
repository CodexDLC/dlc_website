"""
Runner — оркестратор установки.

Flow с двумя коммитами:
1. git init → commit "Install" (ВСЕ файлы шаблона — точка возврата)
2. installers.pre_install + install
3. cleaner → renamer → docker → poetry → scaffolder
4. installers.post_install
5. finalizer → commit "Activate" (чистый проект)

Фишка: первый коммит хранит ВСЕ модули.
Команда `add bot` потом может достать их из git истории.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.init_project.actions.cleaner.cleaner import CleanerAction
from tools.init_project.actions.docker.docker import DockerAction
from tools.init_project.actions.finalizer.finalizer import FinalizerAction
from tools.init_project.actions.poetry.poetry import PoetryAction
from tools.init_project.actions.renamer.renamer import RenamerAction
from tools.init_project.actions.scaffolder.scaffolder import ScaffolderAction
from tools.init_project.installers.bot_installer import BotInstaller
from tools.init_project.installers.django_installer import DjangoInstaller
from tools.init_project.installers.fastapi_installer import FastAPIInstaller
from tools.init_project.installers.shared_installer import SharedInstaller

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext
    from tools.init_project.installers.base import BaseInstaller


def _get_installers(ctx: InstallContext) -> list[BaseInstaller]:
    """Собирает список активных installers на основе выбора."""
    installers: list[BaseInstaller] = []

    # Shared — всегда
    installers.append(SharedInstaller())

    # Backend
    if ctx.backend == "fastapi":
        installers.append(FastAPIInstaller())
    elif ctx.backend == "django":
        installers.append(DjangoInstaller())

    # Bot
    if ctx.include_bot:
        installers.append(BotInstaller())

    return installers


def run(ctx: InstallContext) -> None:
    """Запускает полный flow установки."""

    finalizer = FinalizerAction()

    # ── Phase 0: Git "Install" commit — фиксируем ВСЕ файлы шаблона ──
    if ctx.init_git:
        print("  📸 Creating 'Install' snapshot...")
        finalizer.commit_install(ctx)

    # ── Phase 1: Installers ──
    installers = _get_installers(ctx)

    for installer in installers:
        print(f"  📦 {installer.name} — pre_install...")
        installer.pre_install(ctx)

    for installer in installers:
        print(f"  📦 {installer.name} — install...")
        installer.install(ctx)

    # ── Phase 2: Actions ──
    print("  🧹 Cleaning unused modules...")
    CleanerAction().execute(ctx)

    print("  ✏️  Renaming project...")
    RenamerAction().execute(ctx)

    print("  🐳 Docker setup...")
    DockerAction().execute(ctx)

    print("  📦 Poetry dependencies...")
    PoetryAction().execute(ctx)

    print("  🏗️  Scaffolding...")
    ScaffolderAction().execute(ctx)

    # ── Phase 3: Post-install ──
    for installer in installers:
        print(f"  📦 {installer.name} — post_install...")
        installer.post_install(ctx)

    # ── Phase 4: Finalize — чистка артефактов + "Activate" commit ──
    print("  🎯 Finalizing...")
    finalizer.execute(ctx)
