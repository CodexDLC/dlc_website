"""Installer plugins — по одному на каждый фреймворк/модуль."""

from .base import BaseInstaller
from .bot_installer import BotInstaller
from .django_installer import DjangoInstaller
from .fastapi_installer import FastAPIInstaller
from .shared_installer import SharedInstaller

__all__ = [
    "BaseInstaller",
    "FastAPIInstaller",
    "DjangoInstaller",
    "BotInstaller",
    "SharedInstaller",
]
