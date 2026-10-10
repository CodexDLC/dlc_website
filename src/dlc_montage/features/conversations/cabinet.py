from codex_django.cabinet import DashboardWidget, MetricWidgetData, SidebarItem, TopbarEntry, declare
from codex_django.cabinet.notifications import notification_registry
from codex_django.cabinet.selector.dashboard import DashboardSelector
from codex_django.conversations.cabinet import build_inbox_notification_item
from django.http import HttpRequest
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from .selector.messages import get_status_counts


@notification_registry.register("conversations")  # type: ignore[untyped-decorator]
def _conversations_bell(request: HttpRequest) -> object:
    from features.conversations.selector import get_unread_count

    count = get_unread_count()
    return build_inbox_notification_item(
        count=count,
        url=reverse("cabinet:conversations_inbox"),
        label=str(_("New messages")),
    )


@DashboardSelector.extend(cache_key="conversations_stats", cache_ttl=0)  # type: ignore[untyped-decorator]
def provide_conversations_stats(request: HttpRequest) -> dict[str, MetricWidgetData]:
    """
    Dashboard data provider for conversations metrics.
    """
    counts = get_status_counts()
    return {
        "conversations_stats": MetricWidgetData(
            label=str(_("Messages")),
            value=str(counts["open"] + counts["processed"]),
            trend_value=f"{_('waiting')}: {counts['open']}",
            trend_label=str(_("no response yet")),
            icon="bi-chat-dots",
            url=reverse("cabinet:conversations_inbox"),
        )
    }


declare(
    module="conversations",
    space="staff",
    topbar=TopbarEntry(
        group="services",
        label=str(_("Inbox")),
        icon="bi-envelope",
        url=reverse_lazy("cabinet:conversations_inbox"),
        order=20,
    ),
    sidebar=[
        SidebarItem(
            label=str(_("Compose")),
            url=reverse_lazy("cabinet:conversations_compose"),
            icon="bi-pencil-square",
            order=1,
        ),
        SidebarItem(
            label=str(_("Inbox")),
            url=reverse_lazy("cabinet:conversations_inbox"),
            icon="bi-inbox",
            badge_key="unread_messages_count",
            order=2,
        ),
        SidebarItem(
            label=str(_("Processed")),
            url=reverse_lazy("cabinet:conversations_processed"),
            icon="bi-check2-circle",
            order=3,
        ),
        SidebarItem(
            label=str(_("All")),
            url=reverse_lazy("cabinet:conversations_all"),
            icon="bi-collection",
            order=4,
        ),
    ],
    dashboard_widgets=[
        DashboardWidget(
            template="cabinet/widgets/kpi.html",
            context_key="conversations_stats",
            order=1,
            col="col-lg-3",
        )
    ],
)
