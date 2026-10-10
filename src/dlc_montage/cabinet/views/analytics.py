from typing import Any

from codex_django.cabinet.views import dashboard_view
from django.http import HttpResponse
from django.views.generic import TemplateView

from ..services.analytics import AnalyticsService


def analytics_dashboard_view(request: Any) -> HttpResponse:
    """Wrapper for analytics dashboard to set active module."""
    request.cabinet_module = "analytics"
    return dashboard_view(request)


class AnalyticsReportsView(TemplateView):
    """Страница детальных отчетов."""

    template_name = "cabinet/analytics/reports.html"

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        request.cabinet_module = "analytics"
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Получаем данные детальных отчетов
        context.update(AnalyticsService.get_reports_context(self.request))
        return context
