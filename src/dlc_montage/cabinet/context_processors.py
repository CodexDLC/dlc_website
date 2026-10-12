"""Template context owned by the internal CRM shell."""

from __future__ import annotations

from codex_django.cabinet import cabinet_registry
from django.http import HttpRequest
from features.customer_portal.models import ClientMembership
from features.customer_portal.policies import membership_for
from features.internal_time.policies import can_report, directions_for, is_manager

from cabinet.workspaces import WORKSPACES


def crm_navigation(request: HttpRequest) -> dict[str, object]:
    """Expose only the four approved global CRM spaces to the shell template."""
    membership = membership_for(request.user)
    client_identity = request.user.is_authenticated and ClientMembership.objects.filter(user=request.user).exists()
    allowed = (
        {"staff", *dict(directions_for(request.user))} if can_report(request.user) and not client_identity else set()
    )
    if is_manager(request.user):
        allowed.update({"administration", "customer"})
    elif membership:
        allowed = {"customer"}
    if request.user.is_authenticated and request.user.is_active:
        allowed.add("demo")
    return {
        "SITE_NAME": "DLC Montage",
        "crm_topbar_entries": [
            cabinet_registry.get_module_topbar(slug)
            for slug in ("customer", *(workspace.slug for workspace in WORKSPACES), "demo")
            if slug in allowed and cabinet_registry.get_module_topbar(slug) is not None
        ]
    }
