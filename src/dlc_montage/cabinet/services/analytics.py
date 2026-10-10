from dataclasses import dataclass
from typing import Any

from codex_django.cabinet.selector.dashboard import DashboardSelector
from codex_django.cabinet.types.widgets import ListItem, ListWidgetData, MetricWidgetData
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _


@dataclass
class AnalyticsService:
    @staticmethod
    def get_kpi_metrics() -> dict[str, MetricWidgetData]:
        return {
            "revenue": MetricWidgetData(
                label=_("Выручка за месяц"),
                value="142 500",
                unit="₽",
                trend_value="+12%",
                trend_label="vs прошлый месяц",
                trend_direction="up",
                icon="bi-currency-ruble",
            ),
            "clients": MetricWidgetData(
                label=_("Клиентов всего"),
                value="1 205",
                trend_value="+24",
                trend_label="за неделю",
                trend_direction="up",
                icon="bi-people",
            ),
            "avg_check": MetricWidgetData(
                label=_("Средний чек"),
                value="2 450",
                unit="₽",
                trend_value="-3%",
                trend_label="vs прошлый месяц",
                trend_direction="down",
                icon="bi-receipt",
            ),
        }

    @staticmethod
    def get_chart_data() -> dict[str, dict[str, Any]]:
        return {
            "revenue_chart": {
                "chart_id": "revenueChart",
                "title": "Выручка",
                "subtitle": "последние 7 дней",
                "icon": "bi-graph-up",
                "type": "line",
                "kpi_value": "142 500 ₽",
                "kpi_trend": "+12%",
                "kpi_trend_label": "vs прошлый месяц",
                "chart_labels": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],  # noqa: RUF001
                "chart_data": [12000, 15000, 11000, 18000, 22000, 31000, 28000],
                "color": "#4f46e5",
                "bg_color": "rgba(79, 70, 229, 0.1)",
            },
            "services_donut": {
                "chart_id": "servicesDonut",
                "title": "Популярные услуги",
                "icon": "bi-pie-chart",
                "chart_labels": ["Стрижка", "Окрашивание", "Укладка", "Уход"],
                "chart_data": [45, 30, 15, 10],
                "colors": ["#4f46e5", "#818cf8", "#c7d2fe", "#f1f5f9"],
            },
        }

    @staticmethod
    def get_top_lists() -> dict[str, ListWidgetData]:
        return {
            "top_foremen": ListWidgetData(
                title=_("Топ бригадиров"),
                subtitle="этот месяц",
                icon="bi-star",
                items=[
                    ListItem(label=_("Елена С."), value="120 000 ₽", avatar="ЕС", sublabel="45 записей"),
                    ListItem(label=_("Анна М."), value="98 000 ₽", avatar="АМ", sublabel="38 записей"),
                    ListItem(label=_("Ольга К."), value="75 000 ₽", avatar="ОК", sublabel="30 записей"),
                ],
            ),
            "top_services": ListWidgetData(
                title=_("Топ услуги"),
                subtitle="этот месяц",
                icon="bi-scissors",
                items=[
                    ListItem(label=_("Маникюр с покрытием"), value="24 000 ₽", sublabel="48 раз"),
                    ListItem(label=_("Стрижка женская"), value="18 500 ₽", sublabel="32 раза"),
                    ListItem(label=_("Окрашивание"), value="15 000 ₽", sublabel="12 раз"),
                ],
            ),
        }

    @staticmethod
    def get_reports_context(request: HttpRequest) -> dict[str, object]:
        """Return the complete reports page contract for cabinet analytics."""
        tab = request.GET.get("tab", "revenue")
        active_period = request.GET.get("period", "month")
        active_staff = request.GET.get("staff", "")

        report_tabs = [
            {"key": "revenue", "label": _("Revenue"), "icon": "bi-currency-ruble"},
            {"key": "services", "label": _("Services"), "icon": "bi-scissors"},
            {"key": "foremen", "label": _("Foremen"), "icon": "bi-people"},
        ]
        period_options = [
            {"key": "week", "label": _("Week")},
            {"key": "month", "label": _("Month")},
            {"key": "quarter", "label": _("Quarter")},
        ]
        staff_options = ["All team", "Elena S.", "Anna M.", "Olga K."]
        rows = [
            {"label": "Week 1", "revenue_fmt": "35 000 ₽", "conversion": "68%"},
            {"label": "Week 2", "revenue_fmt": "31 500 ₽", "conversion": "64%"},
            {"label": "Week 3", "revenue_fmt": "40 000 ₽", "conversion": "72%"},
            {"label": "Week 4", "revenue_fmt": "36 000 ₽", "conversion": "64%"},
        ]
        columns = [
            {"key": "label", "label": _("Period"), "bold": True},
            {"key": "revenue_fmt", "label": _("Revenue"), "align": "right"},
            {"key": "conversion", "label": _("Conversion"), "align": "right"},
        ]
        summary_row = {
            "label": _("Total"),
            "revenue_fmt": "142 500 ₽",
            "conversion": "68%",
        }
        return {
            "active_tab": tab,
            "active_period": active_period,
            "active_staff": active_staff,
            "report_title": str(_("Reports")),
            "report_summary": f"Mocked analytics summary for {tab}.",
            "period_label": _("Current reporting period"),
            "report_tabs": report_tabs,
            "period_options": period_options,
            "staff_options": staff_options,
            "columns": columns,
            "rows": rows,
            "summary_row": summary_row,
            "bar_max": 40000,
            "table_summary": {"total_revenue": summary_row["revenue_fmt"]},
        }


# --- Register Providers ---


@DashboardSelector.extend(cache_key="analytics_kpis", cache_ttl=0)  # type: ignore[untyped-decorator]
def provide_analytics_kpis(request: Any) -> Any:
    return AnalyticsService.get_kpi_metrics()


@DashboardSelector.extend(cache_key="analytics_charts", cache_ttl=0)  # type: ignore[untyped-decorator]
def provide_analytics_charts(request: Any) -> Any:
    return AnalyticsService.get_chart_data()


@DashboardSelector.extend(cache_key="analytics_lists", cache_ttl=0)  # type: ignore[untyped-decorator]
def provide_analytics_lists(request: Any) -> Any:
    return AnalyticsService.get_top_lists()
