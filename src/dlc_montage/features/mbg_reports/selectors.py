"""Подготовленные выборки MBG; на первом этапе доступны администраторам."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, F, Q

from features.internal_time.policies import is_manager
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import CableType, WorkType

from .completion_projection import project_accepted_entries
from .models import (
    CURRENT_WEEKLY_EXPORT_TEMPLATE,
    MbgDailyReport,
    MbgReportRevision,
    MbgWorkEntry,
    PerformanceExport,
    WeeklyExport,
)
from .pricing_projection import price_completion_row


def reports_for(user):
    qs = MbgDailyReport.objects.select_related("site__group", "author").prefetch_related(
        "workforce", "entries__participants", "entries__work_type", "entries__cable_type", "entries__route"
    )
    return qs if is_manager(user) else qs.none()


def filtered_reports_for(user, filters):
    """Отфильтровать журнал MBG и подготовить счётчики для списка."""
    qs = reports_for(user).annotate(workforce_count=Count("workforce", distinct=True))
    if filters.get("group"):
        qs = qs.filter(site__group=filters["group"])
    if filters.get("site"):
        qs = qs.filter(site=filters["site"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("date_from"):
        qs = qs.filter(work_date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(work_date__lte=filters["date_to"])
    return qs


def export_groups(query=""):
    """Проекты AC со счётчиками завершённых Standort и сдельных книг."""
    qs = ProjectGroup.objects.filter(has_ac=True, status="active").annotate(
        report_count=Count("ac_objects__mbg_reports", distinct=True),
        accepted_report_count=Count(
            "ac_objects__mbg_reports",
            filter=Q(ac_objects__mbg_reports__status="accepted"),
            distinct=True,
        ),
        completed_site_count=Count(
            "ac_objects",
            filter=Q(ac_objects__status="completed"),
            distinct=True,
        ),
        started_site_count=Count(
            "ac_objects",
            filter=Q(ac_objects__status="started"),
            distinct=True,
        ),
        total_site_count=Count("ac_objects", distinct=True),
        export_count=Count(
            "performance_exports",
            filter=Q(performance_exports__document_type="priced_performance"),
            distinct=True,
        ),
    )
    return qs.filter(Q(name__icontains=query.strip()) | Q(address__icontains=query.strip())) if query else qs


def export_hub_context(
    query="",
    *,
    page_weeks: int | str = 1,
    page_completion: int | str = 1,
    per_page_weeks: int = 8,
    per_page_completion: int = 10,
):
    """Подготовить группы и Standorte для страницы Excel без запросов из view или template."""
    groups = list(export_groups(query))
    preliminary_groups = [group for group in groups if group.accepted_report_count]
    completed_groups = [group for group in groups if group.completed_site_count]

    sites_by_group = {group.pk: [] for group in preliminary_groups}
    sites = (
        AcObject.objects.filter(
            group_id__in=sites_by_group,
            is_active=True,
            mbg_reports__status="accepted",
        )
        .annotate(
            accepted_reports_count=Count(
                "mbg_reports",
                filter=Q(mbg_reports__status="accepted"),
                distinct=True,
            )
        )
        .select_related("group")
        .order_by("group__name", "name", "pk")
        .distinct()
    )
    for site in sites:
        sites_by_group[site.group_id].append(site)

    preliminary_groups_with_sites = [
        {"group": group, "sites": sites_by_group[group.pk]} for group in preliminary_groups
    ]

    weekly_cards_all = weekly_export_cards()
    if query:
        q_norm = query.strip().casefold()
        matched_group_ids = {group.pk for group in groups}
        filtered_cards = []
        for card in weekly_cards_all:
            matches_group = any(metric.group_id in matched_group_ids for metric in card.groups)
            matches_kw = q_norm in f"kw {card.week}" or q_norm in f"kw{card.week}" or q_norm == str(card.week)
            if matches_group or matches_kw:
                filtered_cards.append(card)
        weekly_cards_all = filtered_cards

    paginator_weeks = Paginator(weekly_cards_all, per_page_weeks)
    weekly_cards_p = paginator_weeks.get_page(page_weeks)

    completion_groups_all = work_completion_groups(query)
    paginator_completion = Paginator(completion_groups_all, per_page_completion)
    completion_groups_p = paginator_completion.get_page(page_completion)

    return {
        "preliminary_groups": preliminary_groups,
        "preliminary_groups_with_sites": preliminary_groups_with_sites,
        "total_preliminary_sites": sum(len(item["sites"]) for item in preliminary_groups_with_sites),
        "total_preliminary_reports": sum(group.accepted_report_count for group in preliminary_groups),
        "completed_groups": completed_groups,
        "weekly_cards": weekly_cards_p,
        "weekly_cards_page": weekly_cards_p,
        "work_completion_groups": completion_groups_p,
        "work_completion_groups_page": completion_groups_p,
        "work_completion_history": work_completion_export_history(),
        "page_weeks": page_weeks,
        "page_completion": page_completion,
    }


def work_completion_groups(query=""):
    """Вернуть Anlagen и Standorte, у которых есть текущий принятый снимок MBG."""
    groups = list(export_groups(query))
    sites = list(
        AcObject.objects.filter(group__in=groups, is_active=True, status__in=("started", "completed"))
        .select_related("group")
        .order_by("group__name", "name", "pk")
    )
    reports = list(MbgDailyReport.objects.filter(site__in=sites, status="accepted").only("pk", "site_id", "version"))
    current_revision_report_ids = {
        revision.report_id
        for revision in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version")).only(
            "report_id", "snapshot"
        )
        if revision.snapshot.get("status") == "accepted"
    }
    available_site_ids = {report.site_id for report in reports if report.pk in current_revision_report_ids}
    sites_by_group = defaultdict(list)
    for site in sites:
        if site.pk in available_site_ids:
            sites_by_group[site.group_id].append(site)
    return [{"group": group, "sites": sites_by_group[group.pk]} for group in groups if sites_by_group[group.pk]]


def work_completion_export_history(*, limit=10):
    """Вернуть ограниченную историю клиентских Leistungsnachweise без цен с готовой подписью области."""
    limit = max(1, min(limit, 50))
    artifacts = PerformanceExport.objects.filter(document_type="work_completion").select_related("group", "author")
    history = []
    for artifact in artifacts.order_by("-created_at", "-pk")[:limit]:
        snapshot = artifact.snapshot
        if snapshot.get("scope") == "site" and snapshot.get("sites"):
            scope_label = snapshot["sites"][0].get("site_name", "Объект")
        else:
            scope_label = snapshot.get("group_name") or (artifact.group.name if artifact.group else "Проект")
        history.append({"artifact": artifact, "scope_label": scope_label})
    return history


def priced_performance_exports_for_group(group):
    """Вернуть только историю ценовых Leistungsnachweise и Zwischennachweise Anlage."""
    return PerformanceExport.objects.filter(group=group, document_type="priced_performance").select_related("author")


def work_completion_projection(*, group_id=None, site_id=None):
    """Подготовить нефинансовый клиентский срез только из текущих принятых ревизий MBG."""
    if bool(group_id) == bool(site_id):
        raise ValueError("Укажите ровно одну Anlage или один Standort.")

    sites_qs = AcObject.objects.select_related("group").filter(
        is_active=True,
        status__in=("started", "completed"),
    )
    if group_id:
        sites_qs = sites_qs.filter(group_id=group_id, group__has_ac=True)
    else:
        sites_qs = sites_qs.filter(pk=site_id, group__has_ac=True)
    sites = list(sites_qs.order_by("group__name", "name", "pk"))
    if not sites:
        return {
            "group_id": group_id,
            "sites": [],
            "excluded_reports": [],
            "report_versions": [],
            "accepted_report_count": 0,
        }

    reports = list(
        MbgDailyReport.objects.filter(site__in=sites)
        .only("pk", "site_id", "work_date", "status", "version")
        .order_by("site_id", "work_date", "pk")
    )
    revision_by_current_version = {
        (revision.report_id, revision.version): revision
        for revision in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version")).only(
            "report_id", "version", "snapshot"
        )
    }
    reports_by_site = defaultdict(list)
    excluded_reports = []
    for report in reports:
        if report.status != "accepted":
            excluded_reports.append(
                {
                    "report_id": report.pk,
                    "site_id": report.site_id,
                    "date": str(report.work_date),
                    "reason": "not_accepted",
                }
            )
            continue
        revision = revision_by_current_version.get((report.pk, report.version))
        if revision is None or revision.snapshot.get("status") != "accepted":
            excluded_reports.append(
                {
                    "report_id": report.pk,
                    "site_id": report.site_id,
                    "date": str(report.work_date),
                    "reason": "missing_current_accepted_snapshot",
                }
            )
            continue
        reports_by_site[report.site_id].append((report, revision.snapshot))

    site_snapshots = []
    for site in sites:
        accepted = reports_by_site.get(site.pk, [])
        if not accepted:
            continue
        projected = project_accepted_entries(
            (report.pk, report.version, report.work_date, snapshot) for report, snapshot in accepted
        )
        rows = [
            {
                "kind": row.kind,
                "work_item_id": row.work_item_id,
                "name": row.name,
                "unit": row.unit,
                "quantity": f"{row.quantity:.2f}" if row.quantity is not None else None,
                "actual_person_hours": f"{row.actual_person_hours:.2f}",
                "route": row.route,
                "cable_type": row.cable_type,
                "sources": [
                    {key: value for key, value in source.items() if key != "normative_person_hours"}
                    for source in row.sources
                ],
            }
            for row in projected
        ]
        latest_snapshot = accepted[-1][1]
        site_snapshots.append(
            {
                "site_id": site.pk,
                "site_name": latest_snapshot.get("site_name", site.name),
                "group_name": latest_snapshot.get("group_name", site.group.name),
                "address": latest_snapshot.get("address", site.address),
                "project_number": latest_snapshot.get("project_number", site.project_number),
                "status": site.status,
                "period_start": str(accepted[0][0].work_date),
                "period_end": str(accepted[-1][0].work_date),
                "rows": sorted(
                    rows,
                    key=lambda row: (row["name"].casefold(), row["route"].casefold(), row["cable_type"].casefold()),
                ),
                "unresolved_quantity_count": sum(row["quantity"] is None for row in rows),
            }
        )
    return {
        "group_id": group_id,
        "sites": site_snapshots,
        "excluded_reports": excluded_reports,
        "report_versions": [(report.pk, report.version) for report in reports],
        "accepted_report_count": sum(len(accepted) for accepted in reports_by_site.values()),
    }


@dataclass(frozen=True)
class WeeklyAnlageMetric:
    group_id: int
    name: str
    employee_count: int
    person_hours: Decimal


@dataclass(frozen=True)
class WeeklyExportCard:
    year: int
    week: int
    week_start: date
    week_end: date
    report_count: int
    pending_report_count: int
    person_hours: Decimal
    groups: tuple[WeeklyAnlageMetric, ...]
    latest_export: WeeklyExport | None


@dataclass(frozen=True)
class SiteHistoryEntry:
    report_id: int
    starts_at: time
    ends_at: time
    description: str
    participants: tuple[str, ...]
    person_hours: Decimal
    internal_only: bool


@dataclass(frozen=True)
class SiteHistoryDay:
    work_date: date
    status: str
    entries: tuple[SiteHistoryEntry, ...]
    person_hours: Decimal


@dataclass(frozen=True)
class SiteWorkHistory:
    site: AcObject
    days: tuple[SiteHistoryDay, ...]
    entry_count: int
    person_hours: Decimal


def weekly_export_cards():
    """Собрать недельный журнал AC с метриками по Anlage и последней книгой."""
    weeks = {}
    reports = (
        MbgDailyReport.objects.select_related("site__group")
        .prefetch_related("workforce", "entries")
        .order_by("-work_date", "site__group__name", "pk")
    )
    for report in reports:
        iso = report.work_date.isocalendar()
        week_data = weeks.setdefault(
            (iso.year, iso.week),
            {
                "report_count": 0,
                "pending_report_count": 0,
                "person_hours": Decimal("0"),
                "groups": {},
            },
        )
        group_data = week_data["groups"].setdefault(
            report.site.group_id,
            {
                "name": report.site.group.name,
                "employee_ids": set(),
                "person_hours": Decimal("0"),
            },
        )
        report_hours = sum((entry.actual_person_hours for entry in report.entries.all()), Decimal("0"))
        group_data["employee_ids"].update(employee.pk for employee in report.workforce.all())
        group_data["person_hours"] += report_hours
        week_data["report_count"] += 1
        week_data["person_hours"] += report_hours
        if report.status != "accepted":
            week_data["pending_report_count"] += 1

    latest_exports = {}
    for export in WeeklyExport.objects.filter(
        template_version=CURRENT_WEEKLY_EXPORT_TEMPLATE,
    ).order_by("-pk"):
        latest_exports.setdefault((export.year, export.week), export)

    cards = []
    for (year, week), week_data in sorted(weeks.items(), reverse=True):
        monday = date.fromisocalendar(year, week, 1)
        groups = tuple(
            WeeklyAnlageMetric(
                group_id=group_id,
                name=group_data["name"],
                employee_count=len(group_data["employee_ids"]),
                person_hours=group_data["person_hours"],
            )
            for group_id, group_data in sorted(
                week_data["groups"].items(),
                key=lambda item: item[1]["name"].casefold(),
            )
        )
        cards.append(
            WeeklyExportCard(
                year=year,
                week=week,
                week_start=monday,
                week_end=monday + timedelta(days=6),
                report_count=week_data["report_count"],
                pending_report_count=week_data["pending_report_count"],
                person_hours=week_data["person_hours"],
                groups=groups,
                latest_export=latest_exports.get((year, week)),
            )
        )
    return cards


def employee_day_schedule(*, work_date, employee_ids, exclude_report_id=None):
    """Вернуть сохранённые интервалы MBG выбранных сотрудников за день."""
    selected_ids = {int(employee_id) for employee_id in employee_ids}
    employees = Employee.objects.filter(
        pk__in=selected_ids,
        employment_status="active",
        has_ac_access=True,
    ).order_by("last_name", "first_name", "pk")
    entries = (
        MbgWorkEntry.objects.filter(
            report__work_date=work_date,
            participants__pk__in=selected_ids,
        )
        .select_related("report__site__group")
        .prefetch_related("participants")
        .order_by("starts_at", "ends_at", "pk")
        .distinct()
    )
    if exclude_report_id:
        entries = entries.exclude(report_id=exclude_report_id)

    result = {
        employee.pk: {
            "id": employee.pk,
            "name": str(employee),
            "entries": [],
        }
        for employee in employees
    }
    for entry in entries:
        interval = {
            "start": entry.starts_at.strftime("%H:%M"),
            "end": entry.ends_at.strftime("%H:%M"),
            "group": entry.report.site.group.name,
            "site": entry.report.site.name,
            "report_id": entry.report_id,
        }
        for employee in entry.participants.all():
            if employee.pk in result:
                result[employee.pk]["entries"].append(interval)
    return list(result.values())


def site_work_history(*, site_id, exclude_report_id=None):
    """Вернуть готовую для отображения историю сохранённых работ Standort."""
    site = AcObject.objects.select_related("group").filter(pk=site_id).first()
    if site is None:
        return None

    reports = (
        MbgDailyReport.objects.filter(site_id=site.pk)
        .prefetch_related("entries__participants")
        .order_by("-work_date", "-pk")
    )
    if exclude_report_id:
        reports = reports.exclude(pk=exclude_report_id)

    days = []
    total_entries = 0
    total_hours = Decimal("0")
    for report in reports:
        entries = tuple(
            SiteHistoryEntry(
                report_id=report.pk,
                starts_at=entry.starts_at,
                ends_at=entry.ends_at,
                description=entry.description,
                participants=tuple(str(employee) for employee in entry.participants.all()),
                person_hours=entry.actual_person_hours,
                internal_only=entry.internal_only,
            )
            for entry in report.entries.all()
        )
        day_hours = sum((entry.person_hours for entry in entries), Decimal("0"))
        total_entries += len(entries)
        total_hours += day_hours
        days.append(
            SiteHistoryDay(
                work_date=report.work_date,
                status=report.status,
                entries=entries,
                person_hours=day_hours,
            )
        )
    return SiteWorkHistory(
        site=site,
        days=tuple(days),
        entry_count=total_entries,
        person_hours=total_hours,
    )


@dataclass(frozen=True)
class GroupPositionRow:
    """Одна агрегированная строка обзора работ Anlage."""

    code: str
    name: str
    unit: str
    quantity: Decimal | None
    normative_person_hours: Decimal | None
    actual_person_hours: Decimal
    unit_price: Decimal | None
    amount: Decimal | None
    price_state: str
    work_item_id: int | None
    sources: tuple[dict, ...]


@dataclass(frozen=True)
class SitePositionSummary:
    rows: tuple[GroupPositionRow, ...]
    excluded_reports: tuple[int, ...]


def _catalog_zero_rows(performed_codes, works=None, active_cables=None):
    """Показывать не выполненные позиции, не выдавая цену каталога за согласованную."""
    rows = []
    if works is None:
        works = list(
            WorkType.objects.for_direction("ac").filter(is_active=True, is_break=False).order_by("sort_order", "pk")
        )
    if active_cables is None:
        active_cables = list(CableType.objects.filter(is_active=True).order_by("category", "sort_order", "pk"))
    for work in works:
        if work.code in performed_codes:
            continue
        options = active_cables if work.calculation_rule == WorkType.CalculationRule.CABLE else [None]
        for cable in options:
            rows.append(
                GroupPositionRow(
                    code=f"{work.code}:{cable.code}" if cable else work.code,
                    name=f"{work.name_de} · {cable.name_de}" if cable else work.name_de,
                    unit=cable.unit_display if cable else work.get_unit_display(),
                    quantity=Decimal("0"), normative_person_hours=Decimal("0"),
                    actual_person_hours=Decimal("0"), unit_price=None, amount=Decimal("0"),
                    price_state="unagreed", work_item_id=None, sources=(),
                )
            )
    return rows


def site_position_summary_map(site_ids, *, include_internal=True):
    """Одним набором запросов получить принятые позиции нескольких Standorte."""
    ids = list(site_ids)
    result = {site_id: SitePositionSummary((), ()) for site_id in ids}
    if not ids:
        return result
    reports = list(
        MbgDailyReport.objects.filter(site_id__in=ids, status="accepted")
        .only("pk", "site_id", "work_date", "version")
        .order_by("site_id", "work_date", "pk")
    )
    revisions = {
        (revision.report_id, revision.version): revision.snapshot
        for revision in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
        .only("report_id", "version", "snapshot")
    }
    accepted = defaultdict(list)
    excluded = defaultdict(list)
    works = list(
        WorkType.objects.for_direction("ac").filter(is_active=True, is_break=False).order_by("sort_order", "pk")
    )
    active_cables = list(CableType.objects.filter(is_active=True).order_by("category", "sort_order", "pk"))
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if snapshot and snapshot.get("status") == "accepted":
            accepted[report.site_id].append((report.pk, report.version, report.work_date, snapshot))
        else:
            excluded[report.site_id].append(report.pk)
    for site_id in ids:
        rows = []
        projected = project_accepted_entries(accepted[site_id], include_internal=include_internal)
        for row in projected:
            price = price_completion_row(row)
            source = row.sources[0]
            rows.append(
                GroupPositionRow(
                    code=(f"{source['work_type_code']}:item:{row.work_item_id}" if row.work_item_id
                          else source["work_type_code"]),
                    name=row.name, unit=row.unit, quantity=row.quantity,
                    normative_person_hours=None,
                    actual_person_hours=row.actual_person_hours, unit_price=price.unit_price,
                    amount=price.amount, price_state=price.state, work_item_id=row.work_item_id,
                    sources=row.sources,
                )
            )
        performed_codes = {row.sources[0]["work_type_code"] for row in rows}
        rows.extend(_catalog_zero_rows(performed_codes, works, active_cables))
        result[site_id] = SitePositionSummary(tuple(rows), tuple(excluded[site_id]))
    return result


def _position_summary(site_ids):
    by_site = site_position_summary_map(site_ids)
    performed = [row for summary in by_site.values() for row in summary.rows if row.sources]
    codes = {row.sources[0]["work_type_code"] for row in performed}
    return performed + _catalog_zero_rows(codes)


def group_position_summary(group):
    """Вернуть весь AC-каталог, включая ещё не выполненные нулевые позиции."""
    return _position_summary(AcObject.objects.filter(group=group).values_list("pk", flat=True))


def site_position_summary(site):
    """Вернуть полный AC-каталог и агрегаты одного Standort."""
    return list(site_position_summary_map([site.pk])[site.pk].rows)


def completed_group_position_summary(group):
    """Вернуть каталог и агрегаты только завершённых Standort одной Anlage."""
    return _position_summary(
        AcObject.objects.filter(group=group, status="completed").values_list("pk", flat=True)
    )
