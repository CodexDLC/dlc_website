from codex_django.cabinet import SidebarItem, TopbarEntry, declare
from django.urls import reverse_lazy

declare(
    module="demo",
    space="staff",
    topbar=TopbarEntry(
        group="services",
        label="Demo",
        icon="bi-play-circle",
        url=reverse_lazy("demo:work_types"),
        order=60,
    ),
    sidebar=[
        SidebarItem(label="Tätigkeiten", url=reverse_lazy("demo:work_types"), icon="bi-list-task", order=1),
        SidebarItem(label="Stundennachweis", url=reverse_lazy("demo:reports"), icon="bi-clock-history", order=2),
    ],
)
