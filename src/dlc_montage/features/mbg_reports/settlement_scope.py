"""Pure billing scope for chef settlement exports, separate from employee time."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

from .reporting_dto import AcceptedReportingDataset


def is_settlement_entry(*, internal_only=False, is_break=False, work_type_code="") -> bool:
    """Require explicit external scope and exclude all supported break markers."""
    return not internal_only and not is_break and work_type_code not in {"mittagspause", "pause", "freiraeumen"}


def project_settlement_snapshots(snapshots) -> list[dict]:
    """Copy accepted snapshots into external scope without rewriting their history."""
    result = []
    for snapshot in snapshots:
        entries = [
            entry
            for entry in snapshot.get("entries", [])
            if entry.get("work_type_code") != "photo-documentation"
            and is_settlement_entry(
                internal_only=entry.get("internal_only", False),
                is_break=entry.get("is_break", False),
                work_type_code=entry.get("work_type_code", ""),
            )
        ]
        if entries:
            result.append(deepcopy(dict(snapshot, entries=entries)))
    return result


def project_settlement_dataset(dataset: AcceptedReportingDataset) -> AcceptedReportingDataset:
    """Exclude internal work and breaks from facts, totals and all billing sections.

    Input is the accepted-report read model, including source entry indexes. Its
    position rows already exclude internal work; source keys additionally ensure
    only the retained customer-facing entries can reach this billing projection.
    The original employee-time dataset and historical snapshots remain untouched.
    """

    def project_summary(summary):
        days = []
        allowed_sources = set()
        photo_seen = False
        for day in summary.day_facts:
            entries = tuple(
                entry
                for entry in day.entries
                if is_settlement_entry(
                    internal_only=entry.internal_only,
                    is_break=entry.is_break,
                    work_type_code=entry.work_type_code,
                )
            )
            allowed_sources.update((day.report_id, day.version, entry.entry_index) for entry in entries)
            external_entries = []
            for entry in entries:
                if entry.work_type_code == "photo-documentation":
                    if photo_seen:
                        continue
                    photo_seen = True
                    entry = replace(
                        entry,
                        unit="psch.",
                        quantity=Decimal("1"),
                        actual_person_hours=Decimal("0"),
                        starts_at="",
                        ends_at="",
                        amount=Decimal("0"),
                    )
                external_entries.append(entry)
            entries = tuple(external_entries)
            if not entries:
                continue
            days.append(
                replace(
                    day,
                    entries=entries,
                    total_hours=sum((entry.actual_person_hours for entry in entries), Decimal("0.00")),
                    total_material_amount=sum((entry.amount for entry in entries), Decimal("0.00")),
                )
            )
        if not days:
            return None
        names = sorted(
            {name for day in days for entry in day.entries for name in entry.participant_names if name}
            or {name for day in days for name in day.workforce_names if name}
        )
        return replace(
            summary,
            day_facts=tuple(days),
            position_rows=tuple(
                row
                for row in summary.position_rows
                if row.sources
                and (any if row.code == "photo-documentation" else all)(
                    (source["report_id"], source["report_version"], source["entry_index"]) in allowed_sources
                    for source in row.sources
                )
            ),
            total_hours=sum((day.total_hours for day in days), Decimal("0.00")),
            total_material_amount=sum((day.total_material_amount for day in days), Decimal("0.00")),
            unique_employee_names=tuple(names),
            work_days_count=len(days),
        )

    def project_sites(sites):
        projected = {site_id: project_summary(summary) for site_id, summary in sites.items()}
        return {site_id: summary for site_id, summary in projected.items() if summary is not None}

    all_sites = project_sites(dataset.all_sites)
    periods = {period: project_sites(sites) for period, sites in dataset.sites_by_period.items()}
    periods = {period: sites for period, sites in periods.items() if sites}
    return replace(dataset, all_sites=all_sites, sites_by_period=periods, periods=tuple(sorted(periods)))
