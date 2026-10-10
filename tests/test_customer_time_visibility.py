"""Табель времени остаётся внутренним в общей карточке объекта."""

from types import SimpleNamespace

from django.template.loader import render_to_string


def test_customer_work_tables_hide_internal_hours():
    row = SimpleNamespace(
        name="Montage",
        quantity="1",
        unit="Stk.",
        actual_person_hours="73.25",
        kind="linked",
        work_date="2026-10-10",
        description="Montage",
    )
    group = SimpleNamespace(pk=1, name="Anlage")
    site = SimpleNamespace(pk=1, group_id=1, group=group, name="Haus")
    context = {"group": group, "site": site, "completed_rows": [row], "daily_work": [row], "is_customer_view": True}
    html = render_to_string("projects/includes/_object_common_top.html", context)
    assert "73.25" not in html
    assert "Чел.-ч" not in html
    assert "Montage" in html
    html = render_to_string("projects/includes/_object_common_top.html", {**context, "is_customer_view": False})
    assert "73.25" in html
    assert "Чел.-ч" in html
