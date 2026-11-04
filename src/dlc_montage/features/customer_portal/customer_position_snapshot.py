"""Price-free customer-position snapshots for an explicit review policy."""

import hashlib
import json
from decimal import Decimal

from django.core.exceptions import ValidationError

from features.mbg_reports.customer_billing_selectors import customer_billing_summary
from features.work_catalog.models import CustomerWorkPosition

_SOURCE_FIELDS = ("report_id", "report_version", "entry_index", "work_item_id", "package_id", "completed_quantity")


def _clean_source(source):
    return {
        key: str(source[key]) if key == "completed_quantity" else source[key]
        for key in _SOURCE_FIELDS
        if source.get(key) is not None
    }


def customer_position_snapshot(site, *, include_unperformed: bool):
    """Return canonical customer positions without financial or internal report details."""
    if not isinstance(include_unperformed, bool):
        raise TypeError("include_unperformed must be a bool")
    summary = customer_billing_summary(site)
    if summary.excluded_reports:
        raise ValidationError("Für angenommene Berichte fehlt ein gültiger aktueller Stand.")
    positions = CustomerWorkPosition.objects.order_by("sort_order", "code")
    rows_by_code = {row.code: row for row in summary.rows}
    packages = {}
    extra_nh_cable = False
    for progress in summary.packages:
        code = progress.package.position.code
        if code == "01.0060" and progress.quantity > 0:
            extra_nh_cable = extra_nh_cable or any(
                requirement.work_item.route_id and requirement.work_item.route.code == "nh-existing-cable-extension"
                for requirement in progress.package.requirements.all()
            )
        sources = packages.setdefault(code, [])
        sources.append({"package_id": progress.package.pk})
        for requirement in progress.requirements:
            sources.append(
                {
                    "package_id": progress.package.pk,
                    "work_item_id": requirement.work_item_id,
                    "completed_quantity": str(requirement.completed_quantity),
                }
            )
    rows = []
    for position in positions:
        row = rows_by_code.get(position.code)
        quantity_value = row.quantity if row else Decimal("0")
        if not include_unperformed and (quantity_value is None or quantity_value <= 0):
            continue
        sources = [_clean_source(source) for source in row.sources] if row else []
        sources.extend(packages.get(position.code, []))
        sources = [
            json.loads(value) for value in sorted({json.dumps(source, sort_keys=True) for source in sources if source})
        ]
        quantity = str(Decimal(quantity_value).quantize(Decimal("0.01"))) if quantity_value is not None else None
        display_name = position.name_de
        if position.code == "01.0060" and extra_nh_cable:
            display_name += " · Zusätzliches Kabel zur Verlängerung der Bestandsleitung"
        rows.append(
            {
                "key": f"customer:{position.code}",
                "schema": "customer_positions_v1",
                "code": position.code,
                "name": display_name,
                "name_de": display_name,
                "name_ru": (
                    position.name_ru + " · Zusätzliches Kabel zur Verlängerung der Bestandsleitung"
                    if position.code == "01.0060" and extra_nh_cable
                    else position.name_ru
                ),
                "quantity": quantity,
                "unit": position.unit,
                "kind": "customer_position",
                "route": "",
                "cable_type": "",
                "work_item_id": None,
                "sources": sources,
            }
        )
    return rows


def customer_position_digest(site, *, include_unperformed: bool):
    """Hash only the sanitized projection; changing prices cannot change this digest."""
    snapshot = customer_position_snapshot(site, include_unperformed=include_unperformed)
    data = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
