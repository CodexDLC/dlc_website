"""Месячные итоги исключительно по внутренним отчётам."""

from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from features.internal_time.calculations import duration_minutes, format_minutes
from features.internal_time.models import TeamReport


def monthly_summary(year, month):
    """Принятые часы и предварительные отправленные часы показаны раздельно."""
    first, last = date(year, month, 1), date(year, month, monthrange(year, month)[1])
    reports = (
        TeamReport.objects.filter(work_date__range=(first, last))
        .select_related("project_group")
        .prefetch_related("participants__employee")
    )
    people, groups = {}, {}
    counts = defaultdict(int)
    details = []
    for report in reports:
        counts[report.status] += 1
        if report.status not in ("accepted", "submitted"):
            continue
        for member in report.participants.all():
            minutes = duration_minutes(report.starts_at, report.ends_at) - member.deduction_minutes
            for mapping, key, name in (
                (people, member.employee_id, str(member.employee)),
                (groups, report.project_group_id, report.project_group.name),
            ):
                item = mapping.setdefault(key, {"name": name, "accepted": 0, "submitted": 0})
                if mapping is people:
                    item["hourly_rate"] = member.employee.hourly_rate_eur
                item[report.status] += minutes
            details.append(
                {
                    "date": report.work_date,
                    "name": str(member.employee),
                    "group": report.project_group.name,
                    "direction": report.direction,
                    "minutes": minutes,
                    "status": report.status,
                }
            )
    for item in [*people.values(), *groups.values()]:
        item["accepted_label"] = format_minutes(item["accepted"])
        item["pending_label"] = format_minutes(item["submitted"])
    for item in people.values():
        item["accepted_gross"] = (Decimal(item["accepted"]) * item["hourly_rate"] / 60).quantize(Decimal("0.01"))
        item["submitted_gross"] = (Decimal(item["submitted"]) * item["hourly_rate"] / 60).quantize(Decimal("0.01"))
    return {
        "people": sorted(people.values(), key=lambda p: p["name"]),
        "groups": sorted(groups.values(), key=lambda p: p["name"]),
        "details": details,
        "counts": dict(counts),
        "total": format_minutes(sum(p["accepted"] for p in people.values())),
    }
