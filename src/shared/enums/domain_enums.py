"""
Перечисления доменов (фич) проекта.
Используются Director для маршрутизации между фичами.
"""

from enum import StrEnum


class CoreDomain(StrEnum):
    """Идентификаторы доменов (фич) приложения."""

    COMMANDS = "commands"
    MENU = "menu"
