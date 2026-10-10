"""Read models for the AC project and Standort workspaces."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, Max, Prefetch, Sum
from django.utils.translation import gettext_lazy as _

from features.mbg_reports.models import MbgDailyReport, MbgWorkEntry
from features.work_catalog.localization import WorkNameResolver
from features.work_catalog.models import CableRoute, CableType, WorkType

from .models import AcObject, ProjectGroup, SiteWorkItem
from .selectors import visible_groups

ZERO = Decimal("0")


def internal_daily_work(site):
    """Показать DLC принятые строки, включая работы только внутреннего учёта."""
    from features.mbg_reports.accepted_revisions import load_accepted_current_revisions

    reports = MbgDailyReport.objects.filter(site=site, status="accepted").order_by("work_date", "pk")
    batch = load_accepted_current_revisions(reports, strict=False)
    rows = []
    for report, snapshot in batch.items:
        for entry in snapshot.get("entries", []):
            if entry.get("is_break") or entry.get("work_type_code") == "mittagspause":
                continue
            hours = Decimal(str(entry.get("actual_person_hours") or "0"))
            hourly = entry.get("calculation_rule") in {"actual", "zero"} or entry.get("unit") in {"Std.", "hour"}
            quantity = entry.get("completed_quantity")
            rows.append(
                {
                    "work_date": str(report.work_date),
                    "description": entry.get("description", ""),
                    "quantity": str(hours) if hourly else str(quantity) if quantity is not None else "ungeklärt",
                    "unit": entry.get("unit", ""),
                    "actual_person_hours": hours,
                    "internal_only": bool(entry.get("internal_only", False)),
                }
            )
    return tuple(rows)


@dataclass(frozen=True)
class PlannedWorkRow:
    item: SiteWorkItem
    completed_quantity: Decimal
    actual_person_hours: Decimal
    name: str = ""

    @property
    def remaining_quantity(self):
        return max(self.item.planned_quantity - self.completed_quantity, ZERO)

    @property
    def status(self):
        if not self.item.is_required:
            return "not_required"
        if self.item.completion_confirmed_at and self.completed_quantity >= self.item.planned_quantity:
            return "completed"
        return "partial" if self.completed_quantity > ZERO or self.actual_person_hours > ZERO else "not_started"


@dataclass(frozen=True)
class SitePlanOverview:
    rows: tuple[PlannedWorkRow, ...]
    unresolved_count: int
    excluded_report_count: int

    @property
    def is_ready(self):
        if not self.rows:
            return None
        return self.excluded_report_count == 0 and all(row.status in {"completed", "not_required"} for row in self.rows)


def site_work_plan(site, *, include_internal=True):
    """Показать план и только подтверждённый объём с сохранением неизвестного."""
    from features.mbg_reports.work_items import accepted_work_item_progress

    progress = accepted_work_item_progress(site_id=site.pk, include_internal=include_internal)
    totals = {row.work_item_id: row for row in progress.items}
    names = WorkNameResolver()
    rows = tuple(
        PlannedWorkRow(
            item=item,
            name=names.display(item.label),
            completed_quantity=totals[item.pk].completed_quantity if item.pk in totals else ZERO,
            actual_person_hours=totals[item.pk].actual_person_hours if item.pk in totals else ZERO,
        )
        for item in SiteWorkItem.objects.filter(site=site).select_related("work_type", "route", "cable_type")
    )
    return SitePlanOverview(
        rows=rows,
        unresolved_count=len(progress.unresolved_entries),
        excluded_report_count=len(progress.excluded_reports),
    )


@dataclass(frozen=True)
class TypicalPreviewRow:
    spec: object
    work_name: str
    route_name: str
    cable_name: str
    unit: str
    selected: bool = True
    quantity: str = "1"


def typical_plan_preview(specs):
    """Показать человеку виды, пути, кабели и единицы до создания плана."""
    works = {
        row.code: row for row in WorkType.objects.filter(code__in={s.work_type_code for s in specs}, is_active=True)
    }
    routes = {
        row.code: row
        for row in CableRoute.objects.filter(code__in={s.route_code for s in specs if s.route_code}, is_active=True)
    }
    cables = {
        row.code: row
        for row in CableType.objects.filter(
            code__in={s.cable_type_code for s in specs if s.cable_type_code}, is_active=True
        )
    }
    rows = []
    for spec in specs:
        work = works.get(spec.work_type_code)
        route = routes.get(spec.route_code) if spec.route_code else None
        cable = cables.get(spec.cable_type_code) if spec.cable_type_code else None
        if work is None or (spec.route_code and route is None) or (spec.cable_type_code and cable is None):
            raise ValidationError(_("В типовом плане отсутствует активный вид работы, путь или тип кабеля."))
        rows.append(
            TypicalPreviewRow(
                spec,
                str(work),
                str(route) if route else "",
                str(cable) if cable else "",
                cable.unit_display if cable else work.get_unit_display(),
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class SiteActivity:
    report_count: int = 0
    work_day_count: int = 0
    employee_count: int = 0
    recorded_person_hours: Decimal = ZERO
    accepted_person_hours: Decimal = ZERO
    preliminary_amount: Decimal | None = ZERO
    accepted_amount: Decimal | None = ZERO
    known_subtotal: Decimal = ZERO
    last_work_date: date | None = None


@dataclass(frozen=True)
class SiteCard:
    site: AcObject
    activity: SiteActivity


@dataclass(frozen=True)
class GroupCard:
    group: ProjectGroup
    sites: tuple[SiteCard, ...]
    completed_site_count: int
    recorded_person_hours: Decimal
    preliminary_amount: Decimal | None
    known_subtotal: Decimal
    last_work_date: date | None

    @property
    def site_count(self):
        return len(self.sites)


def site_activity_map(site_ids):
    """Load operational totals for any number of Standorte without N+1 queries."""
    from features.mbg_reports.selectors import site_position_summary_map

    ids = list(site_ids)
    result = {site_id: SiteActivity() for site_id in ids}
    if not ids:
        return result

    report_rows = {
        row["site_id"]: row
        for row in MbgDailyReport.objects.filter(site_id__in=ids)
        .values("site_id")
        .annotate(
            report_count=Count("id"),
            work_day_count=Count("work_date", distinct=True),
            last_work_date=Max("work_date"),
        )
    }
    entry_rows = {
        row["report__site_id"]: row
        for row in MbgWorkEntry.objects.filter(report__site_id__in=ids)
        .values("report__site_id")
        .annotate(
            recorded_person_hours=Sum("actual_person_hours"),
        )
    }
    employee_rows = {
        row["report__site_id"]: row["employee_count"]
        for row in MbgWorkEntry.objects.filter(report__site_id__in=ids)
        .values("report__site_id")
        .annotate(employee_count=Count("participants", distinct=True))
    }
    accepted_positions = site_position_summary_map(ids)
    for site_id in ids:
        reports = report_rows.get(site_id, {})
        entries = entry_rows.get(site_id, {})
        summary = accepted_positions[site_id]
        accepted = [row for row in summary.rows if row.sources]
        known_subtotal = sum((row.amount for row in accepted if row.amount is not None), ZERO)
        amount = (
            None
            if (
                summary.excluded_reports
                or any(row.quantity is None for row in accepted if row.unit != "Std.")
                or any(row.price_state == "unagreed" or row.amount is None for row in accepted)
            )
            else known_subtotal
        )
        result[site_id] = SiteActivity(
            report_count=reports.get("report_count", 0),
            work_day_count=reports.get("work_day_count", 0),
            employee_count=employee_rows.get(site_id, 0),
            recorded_person_hours=entries.get("recorded_person_hours") or ZERO,
            accepted_person_hours=sum((row.actual_person_hours for row in accepted), ZERO),
            preliminary_amount=amount,
            accepted_amount=amount,
            known_subtotal=known_subtotal,
            last_work_date=reports.get("last_work_date"),
        )
    return result


def site_activity(site):
    return site_activity_map([site.pk])[site.pk]


def ac_group_cards(user):
    """Return Anlagen with compact child Standort cards and MBG-only totals."""
    groups = list(
        visible_groups(user, "ac").prefetch_related(
            Prefetch(
                "ac_objects",
                queryset=AcObject.objects.filter(is_active=True).order_by("name", "pk"),
                to_attr="active_ac_objects",
            )
        )
    )
    site_ids = [site.pk for group in groups for site in group.active_ac_objects]
    activities = site_activity_map(site_ids)
    return [build_group_card(group, group.active_ac_objects, activities) for group in groups]


def build_group_card(group, sites=None, activities=None):
    """Build one Anlage card from explicit child data."""
    sites = list(sites if sites is not None else group.ac_objects.filter(is_active=True))
    activities = activities or site_activity_map(site.pk for site in sites)
    site_cards = tuple(SiteCard(site=site, activity=activities[site.pk]) for site in sites)
    last_dates = [card.activity.last_work_date for card in site_cards if card.activity.last_work_date]
    return GroupCard(
        group=group,
        sites=site_cards,
        completed_site_count=sum(card.site.status == "completed" for card in site_cards),
        recorded_person_hours=sum((card.activity.recorded_person_hours for card in site_cards), start=ZERO),
        preliminary_amount=(
            None
            if any(card.activity.preliminary_amount is None for card in site_cards)
            else sum((card.activity.preliminary_amount for card in site_cards), start=ZERO)
        ),
        known_subtotal=sum((card.activity.known_subtotal for card in site_cards), ZERO),
        last_work_date=max(last_dates) if last_dates else None,
    )
