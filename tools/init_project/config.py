"""
Конфигурация инсталлятора.

InstallContext — общий контекст, передаётся во все installers и actions.
MODULES — реестр модулей с путями для cleaner.
"""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _on_rmtree_error(func: object, path: str, exc_info: object) -> None:
    """Снимает read-only и повторяет удаление (Windows fix)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path: Path) -> None:
    """shutil.rmtree с обработкой read-only файлов на Windows."""
    shutil.rmtree(path, onexc=_on_rmtree_error)


@dataclass
class InstallContext:
    """Общий контекст установки — передаётся во все компоненты."""

    project_root: Path
    project_name: str
    backend: str | None  # "fastapi" | "django" | None
    include_bot: bool
    init_git: bool


# ──────────────────────────────────────────────
# Реестр модулей: что удалять если модуль не выбран
# ──────────────────────────────────────────────


@dataclass
class ModuleConfig:
    """Описание одного модуля шаблона."""

    name: str
    src_dirs: list[str] = field(default_factory=list)
    deploy_dirs: list[str] = field(default_factory=list)
    doc_dirs: list[str] = field(default_factory=list)


MODULES: dict[str, ModuleConfig] = {
    "fastapi": ModuleConfig(
        name="FastAPI Backend",
        src_dirs=["src/backend_fastapi"],
        deploy_dirs=["deploy/Fast_api"],
        doc_dirs=[
            "docs/en_EN/architecture/backend_fastapi",
            "docs/en_EN/infrastructure/deployment/fast_api",
            "docs/ru_RU/architecture/backend_fastapi",
        ],
    ),
    "django": ModuleConfig(
        name="Django Backend",
        src_dirs=["src/backend_django"],
        deploy_dirs=["deploy/Django"],
        doc_dirs=[
            "docs/en_EN/architecture/backend_django",
            "docs/ru_RU/architecture/backend_django",
        ],
    ),
    "telegram_bot": ModuleConfig(
        name="Telegram Bot",
        src_dirs=["src/telegram_bot"],
        deploy_dirs=[],
        doc_dirs=[
            "docs/en_EN/architecture/telegram_bot",
            "docs/ru_RU/architecture/telegram_bot",
            "docs/ru_RU/features",
        ],
    ),
}

# Файлы в которых нужно заменить имя проекта
RENAME_TARGETS: list[str] = [
    "pyproject.toml",
    "README.md",
    "README-RU.md",
    ".pre-commit-config.yaml",
]

# Маркер для замены
PROJECT_NAME_MARKER = "project-template"
