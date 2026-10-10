"""Физический объём для заказчика отдельно от учёта рабочего времени."""

from dataclasses import replace
from decimal import Decimal

from features.mbg_reports.completion_projection import project_accepted_entries


def _name(entry):
    return str(entry.get("custom_description") or entry.get("description") or "").strip()


def project_customer_entries(snapshots):
    """Сохранить источники объёма, скрыть часы и распознать согласованные услуги."""
    clean = []
    for report_id, version, work_date, snapshot in snapshots:
        entries = []
        for entry in snapshot.get("entries", []):
            item = dict(entry)
            if _name(item).casefold() == "mittagspause":
                item["is_break"] = True
            entries.append(item)
        clean.append((report_id, version, work_date, {**snapshot, "entries": entries}))
    rows = []
    for row in project_accepted_entries(clean, include_internal=False):
        codes = {s["work_type_code"] for s in row.sources}
        delivery = codes == {"material-delivery"} or (
            codes <= {"", "material-unloading"}
            and row.name in {"Materialabholung und Materialtransport", "Materialabholung Lager (Tiefenerder)"}
        )
        section = codes <= {"sonstige", "sonstige-time-only"} and row.name == (
            "Verlegung des Potentialausgleichsleiters Tiefenerder → HPAS (Querschnitt nicht angegeben)"
        )
        quantity, unit, kind = row.quantity, row.unit, row.kind
        if delivery or section:
            # Historical timed lines record contributors, not separate deliveries/sections.
            quantity = (
                row.quantity
                if delivery and row.kind == "flat"
                else Decimal("1")
                if section
                else Decimal(len({s["work_date"] for s in row.sources}))
            )
            unit, kind = "section" if section else "piece", "service"
        elif (
            row.kind == "unresolved" and len(row.sources) == 1 and row.sources[0].get("completed_quantity") is not None
        ):
            quantity = Decimal(str(row.sources[0]["completed_quantity"]))
        elif row.kind == "hourly":
            quantity, unit = None, ""
        rows.append(replace(row, quantity=quantity, unit=unit, kind=kind))
    return tuple(rows)
