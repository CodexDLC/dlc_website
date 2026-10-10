"""Navigation registrations owned by the internal CRM shell."""

from __future__ import annotations

from codex_django.cabinet import SidebarItem, TopbarEntry, declare
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from cabinet.workspaces import WORKSPACES

for order, workspace in enumerate(WORKSPACES, start=10):
    sidebar = [
        SidebarItem(
            label=section.label,
            url=section.url
            if getattr(section, "url", None) is not None
            else reverse_lazy(
                "cabinet:workspace_page",
                kwargs={"workspace_slug": workspace.slug, "section_slug": section.slug},
            ),
            icon=section.icon,
            order=section_order,
        )
        for section_order, section in enumerate(workspace.sections, start=1)
    ]

    declare(
        module=workspace.slug,
        space="staff",
        # The bundled library permits two groups only. The project template
        # renders these entries as four permanent top-level CRM tabs.
        topbar=TopbarEntry(
            group="services",
            label=workspace.label,
            icon=workspace.icon,
            url=reverse_lazy(
                "cabinet:workspace_page",
                kwargs={"workspace_slug": workspace.slug, "section_slug": "dashboard"},
            ),
            order=order,
        ),
        sidebar=sidebar,
    )

declare(
    module="customer",
    space="staff",
    topbar=TopbarEntry(
        group="services",
        label=_("Кабинет заказчика"),
        icon="bi-building-check",
        url=reverse_lazy("customer_portal:home"),
        order=5,
    ),
    sidebar=[
        SidebarItem(label=_("Мои проекты"), url=reverse_lazy("customer_portal:home"), icon="bi-buildings", order=1),
        SidebarItem(label=_("Объекты"), url=reverse_lazy("customer_portal:objects"), icon="bi-house", order=2),
        SidebarItem(
            label=_("Выполненные работы"), url=reverse_lazy("customer_portal:works"), icon="bi-list-check", order=3
        ),
        SidebarItem(
            label=_("На проверке"), url=reverse_lazy("customer_portal:reviews"), icon="bi-clipboard-check", order=4
        ),
        SidebarItem(
            label=_("Документы"), url=reverse_lazy("customer_portal:documents"), icon="bi-file-earmark-pdf", order=5
        ),
        SidebarItem(
            label=_("История решений"), url=reverse_lazy("customer_portal:audit"), icon="bi-clock-history", order=6
        ),
    ],
)
