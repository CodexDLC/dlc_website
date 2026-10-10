"""Placeholder views for the CRM information architecture prototype."""

from __future__ import annotations

from typing import Any

from codex_django.cabinet.mixins import CabinetTemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from features.internal_time.policies import can_report, directions_for, is_manager

from cabinet.workspaces import get_section, get_workspace


class WorkspaceView(LoginRequiredMixin, CabinetTemplateView):
    """Render a safe, non-functional placeholder for a CRM page."""

    template_name = "cabinet/workspaces/placeholder.html"
    workspace_slug = "ac"
    section_slug = "dashboard"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.workspace_slug = str(kwargs.get("workspace_slug", self.workspace_slug))
        self.section_slug = str(kwargs.get("section_slug", self.section_slug))
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not can_report(request.user):
            raise PermissionDenied
        if self.workspace_slug == "administration" and not is_manager(request.user):
            raise PermissionDenied
        if self.workspace_slug in ("ac", "dc") and self.workspace_slug not in dict(directions_for(request.user)):
            raise PermissionDenied
        workspace = get_workspace(self.workspace_slug)
        if workspace is None:
            raise Http404("Unknown CRM workspace")

        section = get_section(workspace, self.section_slug)
        if section is None:
            raise Http404("Unknown CRM workspace section")

        if getattr(section, "url", None):
            return redirect(section.url)

        self.workspace = workspace
        self.section = section
        self.cabinet_module = workspace.slug
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self) -> list[str]:
        if self.workspace_slug == "ac" and self.section_slug == "dashboard":
            return ["cabinet/workspaces/ac_dashboard.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"workspace": self.workspace, "section": self.section})
        if self.workspace_slug == "ac" and self.section_slug == "dashboard":
            from features.projects.selectors import ac_dashboard_metrics

            context.update(ac_dashboard_metrics(self.request.user))
            context["is_manager"] = is_manager(self.request.user)
        return context
