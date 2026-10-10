"""Customer physical quantities do not reinterpret worker time as delivered volume."""

from copy import deepcopy
from datetime import date
from decimal import Decimal

from features.customer_portal.completion_projection import project_customer_entries
from features.mbg_reports.completion_projection import project_accepted_entries


def test_physical_projection_preserves_internal_time_and_delivery_quantities():
    entries = [
        dict(
            description="Materiallieferung",
            work_type_code="material-delivery",
            unit="flat",
            quantity="2",
            actual_person_hours="4",
        ),
        dict(
            description="Materialabholung Lager (Tiefenerder)",
            work_type_code="material-unloading",
            unit="hour",
            actual_person_hours="2",
        ),
        dict(
            description="Materialabholung Lager (Tiefenerder)",
            work_type_code="material-unloading",
            unit="hour",
            actual_person_hours="2",
        ),
        dict(
            description="Verlegung des Potentialausgleichsleiters Tiefenerder → HPAS (Querschnitt nicht angegeben)",
            work_type_code="sonstige-time-only",
            unit="hour",
            actual_person_hours="0.25",
        ),
        dict(description="Other work", unit="hour", actual_person_hours="3"),
        dict(description="Mittagspause", unit="hour", actual_person_hours="1"),
    ]
    snapshots = [(1, 1, date(2026, 10, 10), {"entries": entries})]
    original = deepcopy(snapshots)
    rows = {r.name: r for r in project_customer_entries(snapshots)}
    assert rows["Materiallieferung"].quantity == Decimal("2")
    assert rows["Materialabholung Lager (Tiefenerder)"].quantity == Decimal("1")
    assert rows[entries[3]["description"]].quantity == Decimal("1")
    assert rows[entries[3]["description"]].unit == "section"
    assert rows["Other work"].quantity is None and rows["Other work"].unit == ""
    assert "Mittagspause" not in rows
    assert rows["Materialabholung Lager (Tiefenerder)"].actual_person_hours == Decimal("4")
    assert snapshots == original
    assert any(r.name == "Mittagspause" for r in project_accepted_entries(snapshots))


def test_historical_delivery_deduplicates_workers_same_day_and_section_across_days():
    delivery = dict(description="Materialabholung und Materialtransport", unit="hour", actual_person_hours="2")
    section = dict(
        description="Verlegung des Potentialausgleichsleiters Tiefenerder → HPAS (Querschnitt nicht angegeben)",
        work_type_code="sonstige",
        unit="hour",
        actual_person_hours="0.25",
    )
    snapshots = [
        (1, 1, date(2026, 10, 10), {"entries": [delivery, section]}),
        (2, 1, date(2026, 10, 10), {"entries": [delivery, section]}),
        (3, 1, date(2026, 10, 11), {"entries": [section]}),
    ]
    rows = {row.name: row for row in project_customer_entries(snapshots)}
    assert rows[delivery["description"]].quantity == Decimal("1")
    assert rows[section["description"]].quantity == Decimal("1")
    assert len(rows[section["description"]].sources) == 3
