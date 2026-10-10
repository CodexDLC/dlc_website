"""Проверки читаемости нефинансового Excel при длинных названиях."""

from io import BytesIO

from features.mbg_reports.exports import build_work_completion_workbook
from openpyxl import load_workbook


def test_completion_long_text_wraps_and_print_area_is_bounded():
    group_name = "Beispielstraße 38, 40 und weiterer Gebäudeteil " * 5
    site = {
        "site_id": 1, "site_name": "Haus 38", "group_name": group_name,
        "project_number": "BEISPIEL-38", "address": "Musterstraße 38, Berlin",
        "status": "completed", "period_start": "2026-09-01", "period_end": "2026-09-18",
        "rows": [{"name": "Verlegung einer zusätzlichen Leitung entlang der vorhandenen Trasse " * 7,
                  "unit": "Pauschale", "quantity": "1.00", "actual_person_hours": "2.50"}],
    }
    snapshot = {"group_name": group_name, "period_label": "01.09.2026 - 18.09.2026", "sites": [site]}
    workbook = load_workbook(BytesIO(build_work_completion_workbook(snapshot)))
    summary, detail = workbook.worksheets
    assert summary.row_dimensions[6].height > 32
    assert detail.row_dimensions[9].height > 32
    assert detail["B2"].alignment.wrap_text
    assert detail.row_dimensions[2].height > 20
    assert summary.print_area and detail.print_area
    assert not summary.sheet_view.showGridLines
    assert not detail.sheet_view.showGridLines
    assert detail["D10"].value == 2.5
