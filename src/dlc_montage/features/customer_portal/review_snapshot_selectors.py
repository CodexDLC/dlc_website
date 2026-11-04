"""Read-only schema-aware freshness of saved customer approvals."""

import hashlib
import json

from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils.translation import gettext as _

from features.mbg_reports.models import MbgDailyReport, MbgReportRevision


def legacy_accepted_snapshot_digest(site):
    """Проверка исторических снимков до перехода на каталог заказчика."""
    reports = list(MbgDailyReport.objects.filter(site=site, status="accepted").order_by("pk"))
    revisions = {
        (row.report_id, row.version): row.snapshot
        for row in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
    }
    data = []
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if not snapshot or snapshot.get("status") != "accepted":
            raise ValidationError(_("У принятого отчёта отсутствует текущий подтверждённый снимок."))
        data.append([report.pk, report.version, snapshot])
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def is_customer_position_snapshot(rows):
    return bool(rows) and all(row.get("schema") == "customer_positions_v1" for row in rows)


def accepted_snapshot_digest(site):
    """Хешировать очищенные позиции и версии принятых отчётов без цен и часов."""
    from .customer_position_snapshot import customer_position_snapshot

    positions = customer_position_snapshot(site, include_unperformed=True)
    versions = list(
        MbgDailyReport.objects.filter(site=site, status="accepted").order_by("pk").values_list("pk", "version")
    )
    return hashlib.sha256(
        json.dumps(
            {"positions": positions, "reports": versions}, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def review_snapshot_is_stale(site, review):
    if review.status == "submitted" and not is_customer_position_snapshot(review.work_snapshot):
        return True
    digest = (
        accepted_snapshot_digest(site)
        if is_customer_position_snapshot(review.work_snapshot)
        else legacy_accepted_snapshot_digest(site)
    )
    return review.snapshot_digest != digest
