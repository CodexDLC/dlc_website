"""Сценарии создания неизменяемых экспортных отчётов MBG."""

import json
import re
from datetime import date, timedelta
from hashlib import sha256

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from features.projects.models import AcObject, ProjectGroup

from . import accepted_revisions
from .export_storage import (
    find_existing_final_hourly_export,
    find_existing_performance_export,
    find_existing_weekly_export,
    store_export_artifact,
)
from .export_workbooks import (
    build_final_hourly_workbook,
    build_performance_workbook,
    build_work_completion_workbook,
    build_workbook,
)
from .models import (
    CURRENT_FINAL_HOURLY_EXPORT_TEMPLATE,
    CURRENT_WEEKLY_EXPORT_TEMPLATE,
    CURRENT_WORK_COMPLETION_EXPORT_TEMPLATE,
    FinalHourlyExport,
    MbgDailyReport,
    PerformanceExport,
    WeeklyExport,
)
from .policies import can_export_reports
from .selectors import site_position_summary_map, work_completion_projection


@transaction.atomic
def generate_work_completion_report(*, actor, group_id=None, site_id=None):
    """Создать неизменяемый клиентский Leistungsnachweis из текущих принятых снимков."""
    if not can_export_reports(actor):
        raise PermissionDenied
    if bool(group_id) == bool(site_id):
        raise ValidationError(_("Выберите один проект или один объект."))
    group = None
    if group_id:
        group = ProjectGroup.objects.select_for_update().filter(pk=group_id, has_ac=True, status="active").first()
        if group is None:
            raise ValidationError(_("Проект не найден или не относится к направлению AC."))
    else:
        site = (
            AcObject.objects.select_for_update()
            .select_related("group")
            .filter(pk=site_id, group__has_ac=True, group__status="active")
            .first()
        )
        if site is None:
            raise ValidationError(_("Объект не найден или не относится к направлению AC."))
        group = site.group
    report_locks = MbgDailyReport.objects.select_for_update()
    report_locks = report_locks.filter(site_id=site_id) if site_id else report_locks.filter(site__group=group)
    list(report_locks.only("pk"))
    projection = work_completion_projection(group_id=group_id, site_id=site_id)
    if not projection["report_versions"]:
        raise ValidationError(_("Для выбранной области нет отчётов MBG."))
    if not projection["accepted_report_count"]:
        if any(item["reason"] == "missing_current_accepted_snapshot" for item in projection["excluded_reports"]):
            raise ValidationError(_("Нет текущих принятых снимков MBG для выбранной области."))
        raise ValidationError(_("Для выбранной области нет принятых отчётов MBG."))
    if not projection["sites"]:
        raise ValidationError(_("Нет текущих принятых снимков MBG для выбранной области."))

    included_dates = [
        date.fromisoformat(site_snapshot[date_key])
        for site_snapshot in projection["sites"]
        for date_key in ("period_start", "period_end")
    ]
    period_label = "—" if not included_dates else f"{min(included_dates):%d.%m.%Y} - {max(included_dates):%d.%m.%Y}"
    snapshot = {
        "document_type": "work_completion",
        "group_id": group.pk if group_id else None,
        "group_name": group.name,
        "scope": "group" if group_id else "site",
        "period_label": period_label,
        "sites": projection["sites"],
        "excluded_reports": projection["excluded_reports"],
    }
    fingerprint = sha256(
        json.dumps(
            {
                "template": CURRENT_WORK_COMPLETION_EXPORT_TEMPLATE,
                "scope": snapshot["scope"],
                "group_id": group_id,
                "site_id": site_id,
                "reports": projection["report_versions"],
                "snapshot": snapshot,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = find_existing_performance_export(fingerprint=fingerprint, document_type="work_completion")
    if existing:
        return existing
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", group.name).strip(". ")[:120] or "Anlage"
    if site_id and projection["sites"]:
        site_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", projection["sites"][0]["site_name"]).strip(". ")[:50]
        safe_name = f"{safe_name} - {site_name}"
    artifact = PerformanceExport(
        group=group,
        document_type="work_completion",
        fingerprint=fingerprint,
        snapshot=snapshot,
        author=actor,
        template_version=CURRENT_WORK_COMPLETION_EXPORT_TEMPLATE,
        filename=f"{safe_name} - Leistungsnachweis Arbeiten.xlsx",
    )
    return store_export_artifact(artifact, build_work_completion_workbook(snapshot))


@transaction.atomic
def generate_week(*, actor, year, week):
    """Одна книга на всю AC-часть и ISO-неделю; повтор возвращает тот же артефакт."""
    if not can_export_reports(actor):
        raise PermissionDenied
    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValidationError(_("Некорректная календарная неделя.")) from exc
    reports = list(
        MbgDailyReport.objects.select_for_update()
        .filter(site__group__has_ac=True, work_date__range=(monday, monday + timedelta(days=6)))
        .order_by("site__group_id", "site_id", "work_date")
    )
    if not reports or any(report.status != "accepted" for report in reports):
        raise ValidationError(_("Для выгрузки нужны принятые отчёты. Проверьте все записи этой недели."))
    batch = accepted_revisions.load_accepted_current_revisions(reports, strict=True)
    snapshots = list(batch.snapshots)
    if any(not s["address"].strip() or not s["project_number"].strip() for s in snapshots):
        raise ValidationError(
            "В принятых отчётах отсутствуют адрес или P/Nr. Заполните объект и сохраните исправленную ревизию отчёта."
        )
    fingerprint = sha256(
        json.dumps(
            {
                "template": CURRENT_WEEKLY_EXPORT_TEMPLATE,
                "year": year,
                "week": week,
                "reports": [(r.pk, r.version) for r in reports],
                "data": snapshots,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = find_existing_weekly_export(fingerprint=fingerprint)
    if existing:
        return existing
    artifact = WeeklyExport(
        year=year,
        week=week,
        fingerprint=fingerprint,
        snapshot=snapshots,
        author=actor,
        template_version=CURRENT_WEEKLY_EXPORT_TEMPLATE,
        filename=f"AC - KW {week:02} - {year}.xlsx",
    )
    return store_export_artifact(artifact, build_workbook(snapshots, year, week))


@transaction.atomic
def generate_final_hours(*, actor, group_id):
    """Сохранить полный Stundennachweis после завершения всей Anlage."""
    if not can_export_reports(actor):
        raise PermissionDenied
    group = ProjectGroup.objects.select_for_update().filter(pk=group_id, has_ac=True, status="active").first()
    if group is None:
        raise ValidationError(_("Anlage не найдена или не имеет направления AC."))

    sites = list(AcObject.objects.select_for_update().filter(group=group, is_active=True).order_by("name", "pk"))
    if not sites or any(site.status != "completed" for site in sites):
        raise ValidationError(_("Итоговый почасовой отчёт доступен, когда завершены все активные Standorte Anlage."))

    reports = list(
        MbgDailyReport.objects.select_for_update().filter(site__in=sites).order_by("site_id", "work_date", "pk")
    )
    if {report.site_id for report in reports} != {site.pk for site in sites}:
        raise ValidationError(_("Для каждого Standort должен быть сохранён хотя бы один отчёт MBG."))
    if any(report.status != "accepted" for report in reports):
        raise ValidationError(_("Для итогового почасового отчёта все отчёты Anlage должны быть приняты."))

    batch = accepted_revisions.load_accepted_current_revisions(reports, strict=True)
    snapshots = list(batch.snapshots)
    if any(not snapshot["address"].strip() or not snapshot["project_number"].strip() for snapshot in snapshots):
        raise ValidationError(_("В отчётах отсутствуют адрес или P/Nr. Заполните данные Standort."))

    period_start = min(report.work_date for report in reports)
    period_end = max(report.work_date for report in reports)
    snapshot = {
        "group_id": group.pk,
        "group_name": group.name,
        "period_start": str(period_start),
        "period_end": str(period_end),
        "reports": snapshots,
    }
    fingerprint = sha256(
        json.dumps(
            {
                "template": CURRENT_FINAL_HOURLY_EXPORT_TEMPLATE,
                "group_id": group.pk,
                "reports": [(report.pk, report.version) for report in reports],
                "data": snapshot,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = find_existing_final_hourly_export(fingerprint=fingerprint)
    if existing:
        return existing

    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", group.name).strip(". ")[:140] or "Anlage"
    filename = f"{safe_name} - Gesamtstundennachweis - {period_start:%Y-%m-%d}-{period_end:%Y-%m-%d}.xlsx"
    artifact = FinalHourlyExport(
        group=group,
        period_start=period_start,
        period_end=period_end,
        fingerprint=fingerprint,
        snapshot=snapshot,
        author=actor,
        template_version=CURRENT_FINAL_HOURLY_EXPORT_TEMPLATE,
        filename=filename,
    )
    return store_export_artifact(artifact, build_final_hourly_workbook(snapshots, period_start, period_end))


@transaction.atomic
def generate_performance_report(
    *,
    actor,
    group_id=None,
    group_ids=None,
    site_ids=None,
    is_preliminary=False,
    include_paid: bool = False,
):
    """Создать Leistungsnachweis (завершённых) или Zwischennachweis (выбранных/активных) Standorte."""
    if not can_export_reports(actor):
        raise PermissionDenied

    if group_id is not None:
        groups = list(ProjectGroup.objects.select_for_update().filter(pk=group_id, has_ac=True))
        if not groups:
            raise ValidationError(_("Anlage не найдена или не имеет направления AC."))
    elif group_ids:
        groups = list(
            ProjectGroup.objects.select_for_update().filter(pk__in=group_ids, has_ac=True).order_by("name", "pk")
        )
        if not groups:
            raise ValidationError(_("Не выбрано ни одной Anlage с направлением AC."))
    else:
        groups = list(ProjectGroup.objects.select_for_update().filter(has_ac=True).order_by("name", "pk"))

    if site_ids:
        qs = AcObject.objects.filter(group__in=groups, is_active=True, pk__in=site_ids)
        if not include_paid:
            qs = qs.filter(is_paid=False)
        target_site_ids = list(qs.values_list("pk", flat=True))
    elif not is_preliminary:
        qs = AcObject.objects.filter(group__in=groups, is_active=True, status="completed")
        if not include_paid:
            qs = qs.filter(is_paid=False)
        target_site_ids = list(qs.values_list("pk", flat=True))
    else:
        qs = AcObject.objects.filter(group__in=groups, is_active=True, mbg_reports__status="accepted")
        if not include_paid:
            qs = qs.filter(is_paid=False)
        target_site_ids = list(qs.values_list("pk", flat=True).distinct())

    sites = list(
        AcObject.objects.select_for_update()
        .select_related("group")
        .filter(pk__in=target_site_ids)
        .order_by("group__name", "name", "pk")
    )
    if not sites:
        if is_preliminary:
            raise ValidationError(_("Выберите хотя бы один Standort с принятыми отчётами для промежуточного отчёта."))
        msg = (
            "Leistungsnachweis verfügbar (завершён), wenn in den ausgewählten Anlagen "
            "ein unbezahlter abgeschlossener Standort vorhanden ist."
            if not include_paid
            else (
                "Leistungsnachweis verfügbar (завершён), wenn in den ausgewählten Anlagen "
                "ein abgeschlossener Standort vorhanden ist."
            )
        )
        raise ValidationError(msg)

    reports = list(
        MbgDailyReport.objects.select_for_update().filter(site__in=sites).order_by("site_id", "work_date", "pk")
    )
    report_site_ids = {report.site_id for report in reports}
    if report_site_ids != {site.pk for site in sites} or any(report.status != "accepted" for report in reports):
        if is_preliminary:
            raise ValidationError(_("Для Zwischennachweis все отчёты выбранных Standorte должны быть приняты."))
        raise ValidationError(_("Для Leistungsnachweis все отчёты завершённых Standorte должны быть приняты."))

    if any(not site.address.strip() or not site.project_number.strip() for site in sites):
        raise ValidationError(_("Для выгрузки заполните адрес и P/Nr всех выбранных Standorte."))

    today_str = timezone.localdate().strftime("%d.%m.%Y")
    doc_type = "zwischennachweis" if is_preliminary else "leistungsnachweis"
    group_name_label = (
        groups[0].name
        if len(groups) == 1
        else ("Alle aktiven Anlagen" if is_preliminary else "Alle abgeschlossenen Anlagen")
    )

    position_rows_by_site = site_position_summary_map([site.pk for site in sites], include_internal=False)

    def _site_snapshot_entry(site):
        summary = position_rows_by_site[site.pk]
        accepted_rows = [r for r in summary.rows if r.sources]
        has_excluded = bool(summary.excluded_reports)
        has_incomplete = (
            has_excluded
            or any(r.quantity is None for r in accepted_rows if r.unit != "Std.")
            or any(r.price_state == "unagreed" or r.amount is None for r in accepted_rows)
        )
        amount_val = None if has_incomplete else "0.00"
        return {
            "site_id": site.pk,
            "site_name": site.name,
            "group_id": site.group_id,
            "group_name": site.group.name,
            "address": site.address,
            "project_number": site.project_number,
            "status": site.status,
            "is_paid": site.is_paid,
            "excluded_reports": list(summary.excluded_reports),
            "known_subtotal": "0.00",
            "amount": amount_val,
            "rows": [
                {
                    "code": row.code,
                    "name": row.name,
                    "unit": row.unit,
                    "quantity": str(row.quantity) if row.quantity is not None else None,
                    "normative_person_hours": (
                        str(row.normative_person_hours) if row.normative_person_hours is not None else None
                    ),
                    "actual_person_hours": str(row.actual_person_hours),
                    "unit_price": str(row.unit_price) if row.unit_price is not None else None,
                    "amount": str(row.amount) if row.amount is not None else None,
                    "price_state": row.price_state,
                    "work_item_id": row.work_item_id,
                    "sources": list(row.sources),
                }
                for row in summary.rows
            ],
        }

    snapshot = {
        "group_id": groups[0].pk if len(groups) == 1 else None,
        "group_name": group_name_label,
        "is_preliminary": is_preliminary,
        "include_paid": include_paid,
        "document_type": doc_type,
        "export_date": today_str,
        "pricing_version": "zero_rates_v1",
        "sites": [_site_snapshot_entry(site) for site in sites],
    }
    template_ver = "ac-perf-zero-1"
    fingerprint = sha256(
        json.dumps(
            {
                "template": template_ver,
                "pricing_version": "zero_rates_v1",
                "include_paid": include_paid,
                "group_ids": [g.pk for g in groups],
                "is_preliminary": is_preliminary,
                "site_ids": [s.pk for s in sites],
                "reports": [(report.pk, report.version) for report in reports],
                "data": snapshot,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = find_existing_performance_export(fingerprint=fingerprint)
    if existing:
        return existing

    suffix = "Zwischennachweis" if is_preliminary else "Leistungsnachweis"
    if len(sites) == 1:
        site_name_safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", sites[0].name).strip(". ")[:40]
        group_name_safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", sites[0].group.name).strip(". ")[:100]
        filename = f"{group_name_safe} - {site_name_safe} - {suffix}.xlsx"
    elif len(groups) == 1:
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", groups[0].name).strip(". ")[:160]
        filename = f"{safe_name or 'Anlage'} - {suffix}.xlsx"
    else:
        filename = f"AC - Gesamt - {suffix}.xlsx"

    artifact = PerformanceExport(
        group=groups[0] if len(groups) == 1 else None,
        fingerprint=fingerprint,
        snapshot=snapshot,
        author=actor,
        template_version=template_ver,
        filename=filename,
    )
    return store_export_artifact(artifact, build_performance_workbook(snapshot))


@transaction.atomic
def generate_site_performance_report(*, actor, site_id, is_preliminary=None, include_paid: bool = False):
    """Сформировать Leistungsnachweis или Zwischennachweis для одного конкретного Standort."""
    site = AcObject.objects.select_related("group").get(pk=site_id)
    if site.is_paid and not include_paid:
        raise ValidationError("Dieser Standort ist bereits bezahlt und von neuen Rechnungsnachweisen ausgeschlossen.")
    if is_preliminary is None:
        is_preliminary = site.status != "completed"
    return generate_performance_report(
        actor=actor,
        group_id=site.group_id,
        site_ids=[site.pk],
        is_preliminary=is_preliminary,
        include_paid=include_paid,
    )
