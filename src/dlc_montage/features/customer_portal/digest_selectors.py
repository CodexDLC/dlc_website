"""Read a compact customer digest from current accepted report snapshots."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from features.mbg_reports.accepted_revisions import load_accepted_current_revisions
from features.mbg_reports.models import MbgDailyReport
from features.projects.read_models import site_work_plan

from .completion_projection import project_customer_entries
from .selectors import sites_for_actor

BERLIN = ZoneInfo("Europe/Berlin")


@dataclass(frozen=True)
class DigestSite:
    name: str
    address: str
    intervals: str
    completed: int
    planned: int


@dataclass(frozen=True)
class CustomerDigest:
    work_date: date
    sites: tuple[DigestSite, ...]
    pending_photo_count: int


def scheduled_work_date(now: datetime) -> date | None:
    """Weekdays at/after 08:00 Berlin; Monday covers Friday, with no weekend mail."""
    local = now.astimezone(BERLIN)
    if local.weekday() >= 5 or local.time() < time(8):
        return None
    return local.date() - timedelta(days=3 if local.weekday() == 0 else 1)


def _intervals(entries):
    # Only wall-clock work intervals, never person-hours or worker identities.
    spans = []
    for entry in entries:
        if entry.get("is_break") or entry.get("work_type_code") in {"mittagspause", "pause"}:
            continue
        try:
            start, end = time.fromisoformat(entry["start"]), time.fromisoformat(entry["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if start < end:
            spans.append((start, end))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return ", ".join(f"{start:%H:%M}–{end:%H:%M}" for start, end in merged) or "Keine Zeitangabe"  # noqa: RUF001


def customer_digest(*, recipient, work_date):
    """Keep customer visibility, accepted revisions and the physical plan authoritative."""
    sites = sites_for_actor(recipient).filter(is_active=True)
    reports = MbgDailyReport.objects.filter(site__in=sites, work_date=work_date, status="accepted").select_related(
        "site", "site__group",
    ).order_by("site__name", "site_id")
    batch = load_accepted_current_revisions(reports, strict=True)
    cards = []
    for report, snapshot in batch.items:
        if not project_customer_entries([(report.pk, report.version, report.work_date, snapshot)]):
            continue
        plan = site_work_plan(report.site, include_internal=False)
        required = [row for row in plan.rows if row.item.is_required]
        cards.append(DigestSite(
            name=report.site.name, address=report.site.address,
            intervals=_intervals(snapshot.get("entries", [])),
            completed=sum(row.is_completed for row in required), planned=len(required),
        ))
    pending = sites.filter(customer_review__status="submitted", stored_photos__isnull=False).distinct().count()
    return CustomerDigest(work_date=work_date, sites=tuple(cards), pending_photo_count=pending)
