"""Чистая проекция выполненных работ из принятых снимков MBG."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CompletionRow:
    kind: str
    work_item_id: int | None
    name: str
    unit: str
    quantity: Decimal | None
    actual_person_hours: Decimal
    route: str
    cable_type: str
    sources: tuple[dict, ...]


def _hourly_name(entry):
    """Использовать исходный снимок пояснения без известного суффикса количества."""
    custom = entry.get("custom_description")
    if custom:
        return custom.strip()
    description = entry.get("description", "")
    try:
        quantity = Decimal(str(entry.get("quantity", "1")))
    except (ArithmeticError, ValueError):
        return description
    if quantity != 1:
        suffix = f" · × {format(quantity.normalize(), 'f')}"  # noqa: RUF001
        if description.endswith(suffix):
            return description[: -len(suffix)]
    return description


def project_accepted_entries(accepted_snapshots, include_internal=False):
    """Группировать физические позиции по ID, а неизвестные строки оставлять раздельно."""
    linked = {}
    hourly = {}
    flat_entries = {}
    unresolved = []
    for report_id, report_version, work_date, snapshot in accepted_snapshots:
        for index, entry in enumerate(snapshot.get("entries", [])):
            if entry.get("is_break") or entry.get("work_type_code") in {"mittagspause", "pause"}:
                continue
            if not include_internal and entry.get("internal_only", False):
                continue
            hours = Decimal(str(entry.get("actual_person_hours", "0")))
            unit = entry.get("unit", "")
            name = entry.get("description", "")
            route = entry.get("route", "")
            cable_type = entry.get("cable_type", "")
            source = {
                "report_id": report_id,
                "report_version": report_version,
                "work_date": str(work_date),
                "entry_index": index,
                "description": name,
                "recorded_quantity": str(entry.get("quantity", "")),
                "actual_person_hours": str(entry.get("actual_person_hours", "0")),
                "normative_person_hours": str(entry.get("normative_person_hours", "0")),
                "work_type_code": entry.get("work_type_code", ""),
                "calculation_rule": entry.get("calculation_rule", ""),
                "unit": unit,
                "route": route,
                "cable_type": cable_type,
                "with_underconstruction": entry.get("with_underconstruction"),
                "standard_connections": entry.get("standard_connections"),
                "heavy_connections": entry.get("heavy_connections"),
                "work_item_id": entry.get("work_item_id"),
                "completed_quantity": entry.get("completed_quantity"),
            }
            if entry.get("calculation_rule") in {"actual", "zero"} or unit in {"Std.", "hour"}:
                hourly_name = _hourly_name(entry)
                key = (source["work_type_code"], hourly_name, "Std.", route, cable_type)
                hourly.setdefault(key, []).append((hours, source))
            elif unit in {"psch.", "flat"} and entry.get("work_item_id") is None:
                flat_name = _hourly_name(entry)
                key = (source["work_type_code"], flat_name, "psch.", route, cable_type)
                try:
                    qty = Decimal(str(entry.get("quantity")))
                except (ArithmeticError, ValueError):
                    qty = None
                if qty is None or not qty.is_finite() or qty < 0:
                    unresolved.append(
                        CompletionRow("unresolved", None, flat_name, "psch.", None, hours, route, cable_type, (source,))
                    )
                    continue
                flat_entries.setdefault(key, []).append((qty, hours, source))
            elif entry.get("work_item_id") is None or entry.get("completed_quantity") is None:
                unresolved.append(
                    CompletionRow("unresolved", None, name, unit, None, hours, route, cable_type, (source,))
                )
            else:
                linked.setdefault(entry["work_item_id"], []).append((hours, source))

    rows = []
    for item_id, contributions in linked.items():
        units = {source["unit"] for _, source in contributions}
        if len(units) != 1:
            for hours, source in contributions:
                unresolved.append(
                    CompletionRow(
                        "unresolved_unit_mismatch", item_id, source["description"], source["unit"], None,
                        hours, source["route"], source["cable_type"], (source,),
                    )
                )
            continue
        latest = contributions[-1][1]
        rows.append(
            CompletionRow(
                "linked", item_id, latest["description"], latest["unit"],
                sum((Decimal(source["completed_quantity"]) for _, source in contributions), Decimal("0")),
                sum((hours for hours, _ in contributions), Decimal("0")), latest["route"], latest["cable_type"],
                tuple(source for _, source in contributions),
            )
        )
    for (_code, name, unit, route, cable_type), contributions in flat_entries.items():
        total_qty = sum((qty for qty, _, _ in contributions), Decimal("0"))
        total_hours = sum((hours for _, hours, _ in contributions), Decimal("0"))
        rows.append(
            CompletionRow(
                "flat", None, name, unit, total_qty, total_hours, route, cable_type,
                tuple(source for _, _, source in contributions),
            )
        )
    for (_code, name, unit, route, cable_type), contributions in hourly.items():
        total_hours = sum((hours for hours, _ in contributions), Decimal("0"))
        rows.append(
            CompletionRow(
                "hourly", None, name, unit, total_hours, total_hours, route, cable_type,
                tuple(source for _, source in contributions),
            )
        )
    return tuple(rows + unresolved)
