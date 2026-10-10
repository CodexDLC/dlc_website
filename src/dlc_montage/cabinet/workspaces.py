"""Static information architecture for the internal CRM shell.

This is presentation-only. Business actions, permissions and domain data
remain in feature applications and will be added after the structure is agreed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class WorkspaceSection:
    slug: str
    label: str
    icon: str
    url: Any = None


@dataclass(frozen=True)
class Workspace:
    slug: str
    label: str
    icon: str
    sections: tuple[WorkspaceSection, ...]


WORKSPACES: tuple[Workspace, ...] = (
    Workspace(
        slug="ac",
        label="AC",
        icon="bi-lightning-charge",
        sections=(
            WorkspaceSection("dashboard", _("Обзор"), "bi-grid-1x2"),
            WorkspaceSection("groups", _("Группы проектов"), "bi-diagram-3"),
            WorkspaceSection("objects", _("AC-объекты"), "bi-buildings"),
            WorkspaceSection("mbg-reports", _("Отчёты MBG"), "bi-clipboard2-check"),
            WorkspaceSection(
                "documents",
                "Документы",
                "bi-file-earmark-spreadsheet",
                url=reverse_lazy("mbg_reports:export_hub"),
            ),
            WorkspaceSection("files", _("Файлы"), "bi-folder2-open"),
        ),
    ),
    Workspace(
        slug="dc",
        label="DC",
        icon="bi-battery-charging",
        sections=(
            WorkspaceSection("dashboard", _("Обзор"), "bi-grid-1x2"),
            WorkspaceSection("groups", _("Группы проектов"), "bi-diagram-3"),
            WorkspaceSection("reports", _("Отчёты DC"), "bi-clipboard2-data"),
            WorkspaceSection("files", _("Файлы"), "bi-folder2-open"),
        ),
    ),
    Workspace(
        slug="staff",
        label=_("Персонал"),
        icon="bi-people",
        sections=(
            WorkspaceSection("dashboard", _("Обзор"), "bi-grid-1x2"),
            WorkspaceSection("employees", _("Сотрудники"), "bi-person-vcard"),
            WorkspaceSection("crews", _("Команды"), "bi-people-fill"),
            WorkspaceSection("time-reports", _("Внутренние отчёты"), "bi-clock-history"),
            WorkspaceSection("hours", _("Часы и подтверждения"), "bi-calendar-week"),
        ),
    ),
    Workspace(
        slug="administration",
        label=_("Администрирование"),
        icon="bi-sliders",
        sections=(
            WorkspaceSection("dashboard", _("Обзор"), "bi-grid-1x2"),
            WorkspaceSection("project-groups", _("Группы проектов"), "bi-diagram-3"),
            WorkspaceSection("clients", _("Заказчики"), "bi-buildings"),
            WorkspaceSection("work-catalog", _("Каталог работ"), "bi-list-check"),
            WorkspaceSection("access", _("Пользователи и права"), "bi-shield-lock"),
            WorkspaceSection("exports", _("Выгрузки"), "bi-file-earmark-spreadsheet"),
            WorkspaceSection("system", _("Настройки системы"), "bi-gear"),
        ),
    ),
)

_WORKSPACES_BY_SLUG = {workspace.slug: workspace for workspace in WORKSPACES}


def get_workspace(slug: str) -> Workspace | None:
    """Return a workspace definition by its stable URL slug."""
    return _WORKSPACES_BY_SLUG.get(slug)


def get_section(workspace: Workspace, slug: str) -> WorkspaceSection | None:
    """Return a section from a workspace by its stable URL slug."""
    return next((section for section in workspace.sections if section.slug == slug), None)
