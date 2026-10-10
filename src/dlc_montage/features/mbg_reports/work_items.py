"""Подтверждённый объём по устойчивым позициям Standort."""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import F

from .completion_projection import project_accepted_entries
from .models import MbgDailyReport, MbgReportRevision


@dataclass(frozen=True)
class WorkItemProgress:
    work_item_id: int
    unit: str
    completed_quantity: Decimal
    actual_person_hours: Decimal


@dataclass(frozen=True)
class UnresolvedWorkEntry:
    report_id: int
    work_date: str
    description: str
    recorded_quantity: str
    actual_person_hours: Decimal
    reason: str


@dataclass(frozen=True)
class SiteWorkProgress:
    items: tuple[WorkItemProgress, ...]
    unresolved_entries: tuple[UnresolvedWorkEntry, ...]
    excluded_reports: tuple["ExcludedWorkReport", ...]


@dataclass(frozen=True)
class ExcludedWorkReport:
    report_id: int
    work_date: str
    reason: str


def accepted_work_item_progress(*, site_id, include_internal=True):
    """Считать текущие принятые снимки; старый объём оставить неразобранным."""
    reports = MbgDailyReport.objects.filter(site_id=site_id, status="accepted").order_by("work_date", "pk")
    revisions = {
        (revision.report_id, revision.version): revision.snapshot
        for revision in MbgReportRevision.objects.filter(
            report__in=reports, version=F("report__version")
        ).only("report_id", "version", "snapshot")
    }
    accepted = []
    excluded = []
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if not snapshot or snapshot.get("status") != "accepted":
            excluded.append(
                ExcludedWorkReport(
                    report_id=report.pk,
                    work_date=str(report.work_date),
                    reason="missing_current_accepted_snapshot",
                )
            )
            continue
        accepted.append((report.pk, report.version, report.work_date, snapshot))
    projected = project_accepted_entries(accepted, include_internal=include_internal)
    items = tuple(
        WorkItemProgress(row.work_item_id, row.unit, row.quantity, row.actual_person_hours)
        for row in sorted((row for row in projected if row.kind == "linked"), key=lambda row: row.work_item_id)
    )
    unresolved = tuple(
        UnresolvedWorkEntry(
            report_id=row.sources[0]["report_id"],
            work_date=row.sources[0]["work_date"],
            description=row.name,
            recorded_quantity=row.sources[0]["recorded_quantity"],
            actual_person_hours=row.actual_person_hours,
            reason="unit_mismatch" if row.kind == "unresolved_unit_mismatch" else "missing_work_item_or_delta",
        )
        for row in projected if row.kind.startswith("unresolved")
    )
    return SiteWorkProgress(items=items, unresolved_entries=unresolved, excluded_reports=tuple(excluded))
