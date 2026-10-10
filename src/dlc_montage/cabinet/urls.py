from django.conf import settings
from django.urls import include, path

from .views.conversations import (
    AllMessagesView,
    ComposeView,
    InboxBulkActionView,
    InboxView,
    ProcessedView,
    ThreadActionView,
    ThreadReplyActionView,
    ThreadView,
    manual_check_view,
)
from .views.site_settings import site_settings_tab_view, site_settings_view
from .views.workspaces import WorkspaceView

app_name = "cabinet"

urlpatterns = [
    path(
        "",
        WorkspaceView.as_view(workspace_slug="ac", section_slug="dashboard"),
        name="workspace_home",
    ),
    path("site/settings/", site_settings_view, name="site_settings"),
    path("site/settings/<str:tab_slug>/", site_settings_tab_view, name="site_settings_tab"),
    path(
        "<slug:workspace_slug>/<slug:section_slug>/",
        WorkspaceView.as_view(),
        name="workspace_page",
    ),
    # Generic library routes stay available for the cabinet runtime.
    path("", include("codex_django.cabinet.urls")),
    path("", include("cabinet.auth_urls")),
    # Existing inbox URLs remain reachable, but are intentionally not part of
    # the CRM prototype navigation.
    path("conversations/", InboxView.as_view(), name="conversations_inbox"),
    path("conversations/processed/", ProcessedView.as_view(), name="conversations_processed"),
    path("conversations/all/", AllMessagesView.as_view(), name="conversations_all"),
    path("conversations/compose/", ComposeView.as_view(), name="conversations_compose"),
    path("conversations/<int:pk>/", ThreadView.as_view(), name="conversations_thread"),
    path("conversations/<int:pk>/reply/", ThreadReplyActionView.as_view(), name="conversations_reply"),
    path("conversations/<int:pk>/action/<str:action>/", ThreadActionView.as_view(), name="conversations_action"),
    path("conversations/actions/bulk/", InboxBulkActionView.as_view(), name="conversations_bulk_action"),
    path("conversations/check-inbox/", manual_check_view, name="conversations_check_inbox"),
]

if getattr(settings, "CODEX_ALLAUTH_ENABLED", False):

    urlpatterns.insert(2, path("", include("allauth.urls")))
