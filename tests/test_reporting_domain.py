from datetime import time
from decimal import Decimal

import pytest


def test_model_free_person_hours_and_breaks():
    from features.reporting.calculations import WorkCalculationSpec, calculate_position

    spec = WorkCalculationSpec(calculation_rule="actual", price_mode="actual_hourly", unit_price=Decimal("35"))
    totals = calculate_position(
        work_type=spec, starts_at=time(7), ends_at=time(8, 15), participant_count=2, quantity=Decimal(1)
    )
    assert totals.actual_person_hours == Decimal("2.50")
    assert totals.amount == Decimal("87.50")
    pause = WorkCalculationSpec(calculation_rule="actual", price_mode="actual_hourly", is_break=True)
    assert (
        calculate_position(
            work_type=pause, starts_at=time(7), ends_at=time(8), participant_count=2, quantity=Decimal(1)
        ).actual_person_hours
        == 0
    )


def test_model_free_validation_rejects_overlapping_worker():
    from features.reporting.validation import EntryInput, ReportValidationError, validate_report_entries

    rows = [
        EntryInput(time(7), time(9), frozenset({1}), Decimal(1)),
        EntryInput(time(8), time(10), frozenset({1}), Decimal(1)),
    ]
    with pytest.raises(ReportValidationError) as error:
        validate_report_entries(rows, workforce_ids={1})
    assert error.value.code == "overlap"


def test_demo_header_replaces_company_contacts():
    from io import BytesIO

    from features.mbg_reports.export_workbooks import build_weekly_workbook
    from openpyxl import load_workbook

    payload = {
        "grouped": {
            1: [
                {
                    "date": "2026-09-14",
                    "site_name": "Demo Standort",
                    "address": "Demo Adresse",
                    "project_number": "DEMO",
                    "entries": [],
                }
            ]
        },
        "week": 38,
        "year": 2026,
        "company_header": {"company_name": "DEMO GmbH", "contact": "Demo", "phone": "", "email": ""},
    }
    book = load_workbook(BytesIO(build_weekly_workbook(payload)))
    texts = [str(cell.value) for sheet in book for row in sheet for cell in row if cell.value is not None]
    assert "DEMO GmbH" in texts
    assert not any("Labodin" in text or "googlemail" in text for text in texts)


@pytest.mark.parametrize(
    ("updates", "code"),
    [
        ({"starts_at": time(7, 5)}, "time_grid"),
        ({"participant_ids": frozenset()}, "participants"),
        ({"participant_ids": frozenset({2})}, "participants_outside_workforce"),
        ({"quantity": Decimal("NaN")}, "quantity"),
        ({"quantity": 0}, "quantity"),
        ({"requires_route": True}, "route_required"),
        ({"requires_cable_type": True}, "cable_required"),
        ({"has_cable_type": True}, "cable_unexpected"),
    ],
)
def test_shared_invalid_row_codes(updates, code):
    from dataclasses import replace

    from features.reporting.validation import EntryInput, ReportValidationError, validate_report_entries

    row = replace(EntryInput(time(7), time(8), frozenset({1}), Decimal(1)), **updates)
    with pytest.raises(ReportValidationError) as error:
        validate_report_entries([row], workforce_ids={1})
    assert error.value.code == code


def test_shared_nonoverlapping_employees_and_boundary_times():
    from features.reporting.validation import EntryInput, validate_report_entries

    validate_report_entries(
        [
            EntryInput(time(7), time(8), frozenset({1}), 1),
            EntryInput(time(7), time(8), frozenset({2}), 1),
            EntryInput(time(8), time(9), frozenset({1}), 1),
        ],
        workforce_ids={1, 2},
    )
