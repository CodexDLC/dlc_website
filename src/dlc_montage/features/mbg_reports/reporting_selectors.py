import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db.models import F

from features.customer_portal.models import SiteReview
from features.mbg_reports.completion_projection import project_accepted_entries
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.mbg_reports.pricing_projection import price_completion_row
from features.mbg_reports.selectors import GroupPositionRow
from features.projects.models import AcObject

from . import accepted_revisions
from .reporting_dto import (
    AcceptedDayFact,
    AcceptedEntryFact,
    AcceptedReportingDataset,
    CuratorReviewFact,
    SiteReportingSummary,
)
from .reporting_facts import calc_entry_amount, calc_fact_hours


def compute_site_snapshot_digest(site: AcObject) -> str:
    """Хешировать только актуальные принятые версии отчётов объекта (совместимо с customer_portal)."""
    reports = list(MbgDailyReport.objects.filter(site=site, status="accepted").order_by("pk"))
    revisions = {
        (row.report_id, row.version): row.snapshot
        for row in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
    }
    data = []
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if not snapshot or snapshot.get("status") != "accepted":
            return ""
        data.append([report.pk, report.version, snapshot])
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def resolve_site_construction_status(site: AcObject) -> str:
    """Строительный статус объекта строго из модели AcObject, без привязки к хардкодным именам."""
    return "Fertiggestellt" if site.status == "completed" else "In Bearbeitung"


def _format_review_date(dt: Any) -> str:
    if not dt:
        return ""
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        from django.utils import timezone

        dt = timezone.localtime(dt)
    return dt.strftime("%d.%m.%Y")


def resolve_curator_review(site: AcObject, current_digest: str | None = None) -> CuratorReviewFact:
    """Определить статус проверки куратора.

    Дефолт строго «In Prüfung» / «Nein», без выдуманных дефектов и дат.
    Техническая приёмка куратора НЕ является разрешением на выплату:
    freigabe строго 'Nein' по умолчанию (только сохранённое человеком решение может дать 'Ja').
    """
    default_review = CuratorReviewFact(
        status="In Prüfung",
        freigabe="Nein",
        note="",
        date="",
    )

    review = SiteReview.objects.filter(site=site).first()
    if not review:
        return default_review

    if review.status == "accepted":
        if current_digest is None:
            try:
                current_digest = compute_site_snapshot_digest(site)
            except Exception:
                current_digest = ""
        if review.snapshot_digest and review.snapshot_digest == current_digest:
            return CuratorReviewFact(
                status="Freigegeben",
                freigabe="Nein",  # Technical acceptance is NOT payment authorization
                note=review.remark or "",
                date=_format_review_date(review.decided_at),
            )
    elif review.status == "returned":
        return CuratorReviewFact(
            status="Nacharbeit erforderlich",
            freigabe="Nein",
            note=review.remark or "",
            date=_format_review_date(review.decided_at),
        )

    return default_review


def load_accepted_reports_dataset(
    *,
    site_ids=None,
    iso_periods=None,
    target_weeks=None,
    reference_year=None,
    include_paid: bool = True,
    include_internal: bool = True,
) -> AcceptedReportingDataset:
    """Загрузить детерминированный датасет принятых отчётов:

    - только текущие подтверждённые ревизии (status='accepted');
    - живые черновики и несовпадающие версии исключаются;
    - группировка строго по кортежам (iso_year, iso_week);
    - физические объёмы берутся из completion_projection через site_position_summary_map;
    - include_paid=True сохраняет оплаченные объекты в сводном регистре.
    - include_internal=True сохраняет строки внутреннего учета в day_facts и проекции.
    """
    reports_qs = (
        MbgDailyReport.objects.filter(status="accepted", site__isnull=False)
        .select_related("site", "site__group")
        .order_by("work_date", "pk")
    )
    if site_ids is not None:
        reports_qs = reports_qs.filter(site_id__in=site_ids)
    if not include_paid:
        reports_qs = reports_qs.filter(site__is_paid=False)

    reports = list(reports_qs)
    if not reports:
        return AcceptedReportingDataset(periods=(), sites_by_period={}, all_sites={}, excluded_report_ids=())

    batch = accepted_revisions.load_accepted_current_revisions(reports, strict=False)

    accepted_reports = []
    excluded_ids = list(batch.excluded_report_ids)

    for report, snapshot in batch.items:
        iso_year, iso_week, _ = report.work_date.isocalendar()
        if iso_periods is not None and (iso_year, iso_week) not in iso_periods:
            continue
        if target_weeks is not None:
            if iso_week not in target_weeks:
                continue
            if reference_year is not None and iso_year != reference_year:
                continue

        accepted_reports.append((report, snapshot, iso_year, iso_week))

    report_snapshot_map = {(r[0].pk, r[0].version): r[1] for r in accepted_reports}

    # Построение day_facts
    # Группировка: period -> site_id -> list of day_facts
    grouped_by_period = defaultdict(lambda: defaultdict(list))
    site_all_days = defaultdict(list)
    site_obj_map = {}

    for report, snapshot, iso_year, iso_week in accepted_reports:
        site = report.site
        site_obj_map[site.pk] = site

        workforce = snapshot.get("workforce") or []
        wf_count = len(workforce)
        wf_names = tuple(w.get("name", "") for w in workforce if w.get("name"))

        entry_facts = []
        day_hours = Decimal("0.00")
        day_material = Decimal("0.00")

        for entry_index, entry_dict in enumerate(snapshot.get("entries") or []):
            if not include_internal and entry_dict.get("internal_only", False):
                continue
            e_hours = calc_fact_hours(entry_dict, wf_count)
            e_amount = calc_entry_amount(entry_dict)
            participants = entry_dict.get("participants") or []
            p_names = tuple(p.get("name", "") for p in participants if p.get("name"))

            # Physical quantity: unknown stays explicit None
            comp_qty_raw = entry_dict.get("completed_quantity")
            if comp_qty_raw is not None and str(comp_qty_raw).strip() != "":
                try:
                    qty = Decimal(str(comp_qty_raw))
                except Exception:
                    qty = None
            else:
                qty = None

            entry_fact = AcceptedEntryFact(
                description=entry_dict.get("description", ""),
                work_type_code=entry_dict.get("work_type_code", ""),
                unit=entry_dict.get("unit", ""),
                quantity=qty,
                actual_person_hours=e_hours,
                amount=e_amount,
                starts_at=entry_dict.get("start") or entry_dict.get("starts_at") or "",
                ends_at=entry_dict.get("end") or entry_dict.get("ends_at") or "",
                participant_names=p_names,
                is_break=bool(
                    entry_dict.get("is_break") or entry_dict.get("work_type_code") in {"mittagspause", "pause"}
                ),
                work_item_id=entry_dict.get("work_item_id"),
                route=entry_dict.get("route", ""),
                cable_type=entry_dict.get("cable_type", ""),
                internal_only=bool(entry_dict.get("internal_only", False)),
                entry_index=entry_index,
            )
            entry_facts.append(entry_fact)
            day_hours += e_hours
            day_material += e_amount

        snap_site_name = snapshot.get("site_name") or site.name
        snap_address = snapshot.get("address") if snapshot.get("address") is not None else (site.address or "")
        snap_proj_num = (
            snapshot.get("project_number")
            if snapshot.get("project_number") is not None
            else (site.project_number or "")
        )
        snap_group_name = snapshot.get("group_name") or (site.group.name if site.group else "")

        day_fact = AcceptedDayFact(
            report_id=report.pk,
            version=report.version,
            work_date=report.work_date,
            iso_year=iso_year,
            iso_week=iso_week,
            site_id=site.pk,
            site_name=snap_site_name,
            address=snap_address,
            project_number=snap_proj_num,
            group_name=snap_group_name,
            workforce_names=wf_names,
            entries=tuple(entry_facts),
            total_hours=day_hours.quantize(Decimal("0.01")),
            total_material_amount=day_material.quantize(Decimal("0.01")),
        )
        grouped_by_period[(iso_year, iso_week)][site.pk].append(day_fact)
        site_all_days[site.pk].append(day_fact)

    # Строим SiteReportingSummary для каждого объекта
    def build_summary(site, days):
        accepted_tuples = [
            (d.report_id, d.version, d.work_date, report_snapshot_map.get((d.report_id, d.version), {})) for d in days
        ]
        projected = project_accepted_entries(accepted_tuples, include_internal=False)
        perf_rows = []
        for row in projected:
            price = price_completion_row(row)
            source = row.sources[0]
            perf_rows.append(
                GroupPositionRow(
                    code=(
                        f"{source['work_type_code']}:item:{row.work_item_id}"
                        if row.work_item_id
                        else source["work_type_code"]
                    ),
                    name=row.name,
                    unit=row.unit,
                    quantity=row.quantity,
                    normative_person_hours=None,
                    actual_person_hours=row.actual_person_hours,
                    unit_price=price.unit_price,
                    amount=price.amount,
                    price_state=price.state,
                    work_item_id=row.work_item_id,
                    sources=row.sources,
                )
            )

        latest_day = days[-1] if days else None
        s_site_name = latest_day.site_name if latest_day else site.name
        s_address = latest_day.address if latest_day else (site.address or "")
        s_proj_num = latest_day.project_number if latest_day else (site.project_number or "")
        s_group_name = latest_day.group_name if latest_day else (site.group.name if site.group else "")

        all_emp_names = sorted(
            {p for d in days for e in d.entries for p in e.participant_names if p}
            or {w for d in days for w in d.workforce_names if w}
        )
        total_h = sum((d.total_hours for d in days), Decimal("0.00")).quantize(Decimal("0.01"))
        total_mat = sum((d.total_material_amount for d in days), Decimal("0.00")).quantize(Decimal("0.01"))
        return SiteReportingSummary(
            site_id=site.pk,
            site_name=s_site_name,
            address=s_address,
            project_number=s_proj_num,
            group_name=s_group_name,
            construction_status=resolve_site_construction_status(site),
            is_completed=(site.status == "completed"),
            day_facts=tuple(days),
            curator_review=resolve_curator_review(site),
            position_rows=tuple(perf_rows),
            total_hours=total_h,
            total_material_amount=total_mat,
            unique_employee_names=tuple(all_emp_names),
            work_days_count=len(days),
            is_paid=getattr(site, "is_paid", False),
        )

    all_sites_summary = {sid: build_summary(site_obj_map[sid], days) for sid, days in site_all_days.items()}

    sites_by_period = {}
    for period, sites_map in grouped_by_period.items():
        sites_by_period[period] = {sid: build_summary(site_obj_map[sid], days) for sid, days in sites_map.items()}

    sorted_periods = tuple(sorted(sites_by_period.keys()))

    return AcceptedReportingDataset(
        periods=sorted_periods,
        sites_by_period=sites_by_period,
        all_sites=all_sites_summary,
        excluded_report_ids=tuple(excluded_ids),
    )
