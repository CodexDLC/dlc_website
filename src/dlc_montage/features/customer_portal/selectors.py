"""Безценовые клиентские проекции и фильтрация по явному назначению."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Sequence

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Max, Q

from features.integrations.nextcloud.services import get_site_photo_cache_key
from features.internal_time.policies import is_manager
from features.mbg_reports.completion_projection import project_accepted_entries
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, ProjectGroup
from features.projects.read_models import site_work_plan
from features.work_catalog.models import WorkType

from .models import PlanProposal, SiteReview
from .policies import membership_for
from .services import accepted_snapshot_digest


def groups_for_actor(actor):
    """Вернуть только свои Anlagen или весь набор для администратора."""
    queryset = ProjectGroup.objects.select_related("client").filter(has_ac=True).exclude(status="deleted")
    if is_manager(actor):
        return queryset
    membership = membership_for(actor)
    return queryset.filter(client_id=membership.client_id) if membership else queryset.none()


def filtered_groups_for_actor(
    actor,
    *,
    search: str = "",
    status: str = "active",
    direction: str = "",
):
    """Фильтрация групп для главной страницы кабинета заказчика."""
    queryset = groups_for_actor(actor).annotate(
        sites_count=Count("ac_objects", filter=Q(ac_objects__is_active=True), distinct=True)
    )
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(address__icontains=search))

    if status == "completed":
        queryset = queryset.filter(status="completed")
    elif status == "all":
        pass  # already excludes deleted
    else:  # default active
        queryset = queryset.filter(status="active")

    if direction == "ac":
        queryset = queryset.filter(has_ac=True)
    elif direction == "dc":
        queryset = queryset.filter(has_dc=True)

    return queryset.order_by("name", "pk")


def sites_for_actor(actor):
    """Наследовать границу видимости Standort от Anlage."""
    return AcObject.objects.select_related("group", "group__client").filter(group__in=groups_for_actor(actor))


def filtered_sites_for_actor(
    actor,
    *,
    search: str = "",
    group_id: int | str | None = None,
    status: str = "all",
    sort: str = "activity",
):
    """Фильтрация и сортировка объектов заказчика до пагинации."""
    queryset = sites_for_actor(actor).select_related("group", "group__client", "customer_review")

    if group_id:
        scoped_group = groups_for_actor(actor).filter(pk=group_id).first()
        if scoped_group is None:
            return queryset.none()
        queryset = queryset.filter(group=scoped_group)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(address__icontains=search)
            | Q(project_number__icontains=search)
            | Q(group__name__icontains=search)
        )

    if status == "in_review":
        queryset = queryset.filter(customer_review__status="submitted")
    elif status == "completed":
        queryset = queryset.filter(status="completed")
    elif status == "all":
        pass
    elif status in {"not_started", "started"}:
        queryset = queryset.filter(status=status)
    else:  # default non_completed
        queryset = queryset.filter(status__in=["not_started", "started"])

    if sort == "name":
        queryset = queryset.order_by("name", "pk")
    else:  # default activity: latest changes based on actual report dates
        queryset = queryset.annotate(latest_report_date=Max("mbg_reports__work_date")).order_by(
            F("latest_report_date").desc(nulls_last=True), "-pk"
        )

    return queryset


def attach_site_plan_progress(sites: Sequence[AcObject]) -> None:
    """Определить прогресс принятого плана для списка Standorte без N+1."""
    from features.mbg_reports.work_items import accepted_work_item_progress

    for site in sites:
        items = list(site.work_items.filter(is_required=True))
        if not items:
            site.plan_progress = None
            continue
        progress = accepted_work_item_progress(site_id=site.pk, include_internal=False)
        totals = {row.work_item_id: row for row in progress.items}
        completed = sum(
            1
            for item in items
            if item.completion_confirmed_at
            and item.pk in totals
            and totals[item.pk].completed_quantity >= item.planned_quantity
        )
        site.plan_progress = f"{completed}/{len(items)}"
        site.plan_progress_percent = round(completed / len(items) * 100) if items else 0


@dataclass(frozen=True)
class CustomerDailyWork:
    """Одна разрешённая клиенту строка принятого дневного отчёта."""

    work_date: str
    description: str
    quantity: str
    unit: str
    actual_person_hours: Decimal


def accepted_daily_work(site, *, iso_year: int | None = None, iso_week: int | None = None):
    """Читать только текущие принятые снимки без ставок, сумм и имён работников."""
    reports = _current_accepted_snapshots(site)
    rows = []
    for _report_id, _version, work_date, snapshot in reports:
        if iso_year is not None and iso_week is not None:
            iso = work_date.isocalendar()
            if (iso.year, iso.week) != (iso_year, iso_week):
                continue
        for entry in snapshot.get("entries", []):
            if entry.get("is_break") or entry.get("work_type_code") == "mittagspause":
                continue
            if entry.get("internal_only", False):
                continue
            completed_quantity = entry.get("completed_quantity")
            is_hourly = entry.get("calculation_rule") in {"actual", "zero"} or entry.get("unit") in {"Std.", "hour"}
            quantity = (
                str(entry.get("actual_person_hours") or "0")
                if is_hourly
                else str(completed_quantity)
                if completed_quantity is not None
                else "ungeklärt"
            )
            rows.append(
                CustomerDailyWork(
                    work_date=str(work_date),
                    description=str(entry.get("description", "")),
                    quantity=quantity,
                    unit=str(entry.get("unit", "")),
                    actual_person_hours=Decimal(str(entry.get("actual_person_hours") or "0")),
                )
            )
    return tuple(rows)


def _current_accepted_snapshots(site):
    """Подготовить только текущие версии с валидным принятым снимком."""
    reports = list(MbgDailyReport.objects.filter(site=site, status="accepted").order_by("work_date", "pk"))
    revisions = {
        (revision.report_id, revision.version): revision.snapshot
        for revision in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
    }
    accepted = []
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if not snapshot or snapshot.get("status") != "accepted":
            continue
        accepted.append((report.pk, report.version, report.work_date, snapshot))
    return tuple(accepted)


def accepted_completion_rows(site, *, iso_year: int | None = None, iso_week: int | None = None):
    """Получить агрегаты принятых работ из того же безценового контракта."""
    snapshots = _current_accepted_snapshots(site)
    if iso_year is not None and iso_week is not None:
        snapshots = tuple(s for s in snapshots if s[2].isocalendar()[:2] == (iso_year, iso_week))
    return project_accepted_entries(snapshots, include_internal=False)


def customer_available_weeks(site) -> tuple[tuple[int, int], ...]:
    """Вернуть отсортированные уникальные (ISO-год, ISO-неделя) для принятых отчётов объекта."""
    snapshots = _current_accepted_snapshots(site)
    weeks = {s[2].isocalendar()[:2] for s in snapshots}
    return tuple(sorted(weeks, reverse=True))


@dataclass(frozen=True)
class WorksJournalSiteCard:
    site: AcObject
    work_date: date
    work_date_str: str
    work_rows_count: int


@dataclass(frozen=True)
class WorksJournalDayGroup:
    work_date: date
    work_date_str: str
    site_cards: tuple[WorksJournalSiteCard, ...]


def works_journal_days(
    actor,
    *,
    group_id: int | str | None = None,
    site_id: int | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int | str = 1,
    per_page: int = 7,
):
    """Построение структурированного журнала работ с группировкой по уникальным дням."""
    from features.mbg_reports.accepted_revisions import load_accepted_current_revisions

    allowed_sites = sites_for_actor(actor).select_related("group")

    if group_id:
        scoped_group = groups_for_actor(actor).filter(pk=group_id).first()
        if scoped_group is None:
            return Paginator([], per_page).get_page(page), ()
        allowed_sites = allowed_sites.filter(group=scoped_group)

    if site_id:
        scoped_site = allowed_sites.filter(pk=site_id).first()
        if scoped_site is None:
            return Paginator([], per_page).get_page(page), ()
        allowed_sites = allowed_sites.filter(pk=scoped_site.pk)

    reports_qs = MbgDailyReport.objects.filter(site__in=allowed_sites, status="accepted")

    if date_from:
        reports_qs = reports_qs.filter(work_date__gte=date_from)
    if date_to:
        reports_qs = reports_qs.filter(work_date__lte=date_to)

    unique_dates = list(reports_qs.order_by("-work_date").values_list("work_date", flat=True).distinct())

    paginator = Paginator(unique_dates, per_page)
    days_page = paginator.get_page(page)
    current_dates = list(days_page.object_list)

    if not current_dates:
        return days_page, ()

    reports = list(
        reports_qs.filter(work_date__in=current_dates)
        .select_related("site", "site__group")
        .order_by("-work_date", "site__name", "pk")
    )

    batch = load_accepted_current_revisions(reports, strict=False)

    site_counts_by_date = defaultdict(lambda: defaultdict(int))
    sites_by_id = {}

    for report, snapshot in batch.items:
        sites_by_id[report.site_id] = report.site
        valid_rows = sum(
            1
            for entry in snapshot.get("entries", [])
            if not (
                entry.get("is_break")
                or entry.get("work_type_code") == "mittagspause"
                or entry.get("internal_only", False)
            )
        )
        site_counts_by_date[report.work_date][report.site_id] += valid_rows

    day_groups = []
    for w_date in current_dates:
        site_map = site_counts_by_date.get(w_date, {})
        site_cards = []
        for s_id, count in site_map.items():
            s_obj = sites_by_id[s_id]
            site_cards.append(
                WorksJournalSiteCard(
                    site=s_obj,
                    work_date=w_date,
                    work_date_str=w_date.isoformat(),
                    work_rows_count=count,
                )
            )
        site_cards.sort(key=lambda sc: sc.site.name)
        day_groups.append(
            WorksJournalDayGroup(
                work_date=w_date,
                work_date_str=w_date.isoformat(),
                site_cards=tuple(site_cards),
            )
        )

    return days_page, tuple(day_groups)


def customer_documents_context(
    actor,
    *,
    search_group: str = "",
    search_pdf: str = "",
    page_groups: int | str = 1,
    page_pdf: int | str = 1,
    per_page: int = 20,
):
    """Данные для отображения раздела «Документы» с раздельной пагинацией."""
    from features.project_media.models import ProjectFile

    groups = groups_for_actor(actor).prefetch_related("ac_objects").order_by("name", "pk")
    if search_group:
        groups = groups.filter(Q(name__icontains=search_group) | Q(address__icontains=search_group))

    files = (
        ProjectFile.objects.filter(
            group__in=groups_for_actor(actor), customer_visible=True, content_type="application/pdf"
        )
        .select_related("group", "site")
        .order_by("-created_at", "-pk")
    )
    if search_pdf:
        files = files.filter(
            Q(original_name__icontains=search_pdf)
            | Q(caption__icontains=search_pdf)
            | Q(group__name__icontains=search_pdf)
            | Q(site__name__icontains=search_pdf)
        )

    paginator_groups = Paginator(groups, per_page)
    paginator_pdf = Paginator(files, per_page)

    groups_p = paginator_groups.get_page(page_groups)
    files_p = paginator_pdf.get_page(page_pdf)

    return {
        "groups": groups_p,
        "groups_page": groups_p,
        "files": files_p,
        "files_page": files_p,
        "search_group": search_group,
        "search_pdf": search_pdf,
    }


@dataclass(frozen=True)
class CustomerSiteDetail:
    """Готовая проекция карточки без финансовых полей."""

    site: AcObject
    plan: object
    daily_work: tuple[CustomerDailyWork, ...]
    completed_rows: tuple
    review: SiteReview | None
    review_stale: bool
    review_rows: tuple
    proposals: tuple[PlanProposal, ...]


def get_cached_photo_summary(site: AcObject) -> dict[str, Any] | None:
    """Вернуть только закешированную сводку фотофиксации без сетевых вызовов WebDAV."""
    return cache.get(get_site_photo_cache_key(site))


def customer_site_detail(site):
    """Собрать план, выполненное и отдельную проверку заказчика."""
    review = SiteReview.objects.filter(site=site).first()
    stale = False
    if review and review.status in {"submitted", "accepted"}:
        try:
            stale = review.snapshot_digest != accepted_snapshot_digest(site)
        except ValidationError:
            stale = True
    return CustomerSiteDetail(
        site=site,
        plan=site_work_plan(site, include_internal=False),
        daily_work=accepted_daily_work(site),
        completed_rows=accepted_completion_rows(site),
        review=review,
        review_stale=stale,
        review_rows=tuple(
            {
                **row,
                "unit_label": dict(WorkType.Unit.choices).get(row["unit"], row["unit"]),
                **review.item_decisions.get(row["key"], {}),
            }
            for row in review.work_snapshot
        )
        if review
        else (),
        proposals=tuple(PlanProposal.objects.filter(site=site).select_related("proposed_by", "decided_by")),
    )
