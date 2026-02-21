"""
BaseInstaller — ABC интерфейс для всех installer-плагинов.

Каждый installer реализует три фазы:
  pre_install  — проверки, установка зависимостей
  install      — основная работа (создание структур, шаблонизация)
  post_install — валидация, чистка
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class BaseInstaller(ABC):
    """Базовый интерфейс installer-плагина."""

    name: str = "BaseInstaller"

    def pre_install(self, ctx: InstallContext) -> None:  # noqa: B027
        """Фаза 1: проверки и подготовка. Override при необходимости."""

    @abstractmethod
    def install(self, ctx: InstallContext) -> None:
        """Фаза 2: основная установка. Обязательна к реализации."""
        ...

    def post_install(self, ctx: InstallContext) -> None:  # noqa: B027
        """Фаза 3: валидация и чистка. Override при необходимости."""
