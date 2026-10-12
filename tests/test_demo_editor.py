"""The demo uses the AC editor controls while retaining independent persistence."""

from datetime import time

import pytest
from django.urls import reverse
from features.demo import services
from features.mbg_reports.models import MbgDailyReport, MbgWorkEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo_editor(client, django_user_model):
    actor = django_user_model.objects.create_user(username="demo-editor")
    client.force_login(actor)
    workspace = services.ensure_workspace(actor)
    people = list(workspace.employees.all())[:2]
    data = {
        "date": "2026-10-12",
        "site_name": "Unfertiger Standort",
        "address": "Musteradresse",
        "project_number": "DEMO-UI",
        "workforce": [person.pk for person in people],
        "entries-TOTAL_FORMS": "2",
        "entries-INITIAL_FORMS": "0",
        "entries-MIN_NUM_FORMS": "1",
        "entries-MAX_NUM_FORMS": "100",
        "entries-0-work_type": workspace.work_types.filter(is_break=False).first().pk,
        "entries-0-participants": [people[0].pk],
        "entries-0-starts_at": "07:00",
        "entries-0-ends_at": "08:00",
        "entries-0-quantity": "2.50",
        "entries-0-description": "Erste Arbeit",
        "entries-1-work_type": "",
        "entries-1-participants": [people[1].pk],
        "entries-1-starts_at": "08:00",
        "entries-1-ends_at": "08:45",
        "entries-1-quantity": "",
        "entries-1-description": "Unvollständige zweite Arbeit",
    }
    return workspace, data


def test_demo_renders_actual_ac_editor_without_crm_endpoints(client, demo_editor):
    response = client.get(reverse("demo:report_new"))
    html = response.content.decode()
    assert "mbg_reports/js/editor.js" in html
    assert "mbg_reports/css/editor.css" in html
    assert "internal_time/css/reports.css" in html
    assert "data-day-workforce" in html and "data-entry-participants" in html
    assert "data-person-picker" in html and "data-work-summary-body" in html
    assert "data-mbg-action-bar" in html and 'value="move:0:up"' in html
    assert 'step="900"' in html
    assert "data-availability-url" not in html and "data-work-item-url" not in html
    assert 'name="action" value="submit"' not in html
    assert "Strg" not in html and "data-demo-form" not in html
    editor_html = html.split('<section id="mbg-editor">', 1)[1].split("</form>", 1)[0]
    assert not any("\u0400" <= char <= "\u04ff" for char in editor_html)
    row = response.context["formset"].forms[0]
    assert row["starts_at"].value() == time(7)
    assert row["ends_at"].value() == time(7, 15)
    assert not response.context["form"]["workforce"].value()


@pytest.mark.parametrize(
    "action, expected",
    [
        ("move:1:up", ["Unvollständige zweite Arbeit", "Erste Arbeit"]),
        ("move:0:down", ["Unvollständige zweite Arbeit", "Erste Arbeit"]),
        ("remove:0", ["Unvollständige zweite Arbeit"]),
    ],
)
def test_card_actions_preserve_incomplete_fields_without_saving(client, demo_editor, action, expected):
    workspace, data = demo_editor
    counts = (workspace.reports.count(), MbgDailyReport.objects.count(), MbgWorkEntry.objects.count())
    response = client.post(reverse("demo:report_new"), {**data, "action": action}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "<html" not in response.content.decode()
    formset = response.context["formset"]
    assert not formset.is_bound
    assert [form["description"].value() for form in formset] == expected
    incomplete = next(form for form in formset if form["description"].value() == "Unvollständige zweite Arbeit")
    assert incomplete["participants"].value() == [str(data["entries-1-participants"][0])]
    assert incomplete["work_type"].value() == ""
    assert response.context["form"]["site_name"].value() == data["site_name"]
    assert counts == (workspace.reports.count(), MbgDailyReport.objects.count(), MbgWorkEntry.objects.count())


def test_add_uses_previous_end_day_people_and_no_extra_blank_card(client, demo_editor):
    workspace, data = demo_editor
    response = client.post(reverse("demo:report_new"), {**data, "action": "add"}, HTTP_HX_REQUEST="true")
    rows = response.context["formset"].forms
    assert len(rows) == 3
    assert rows[0]["quantity"].value() == "2.50"
    assert rows[1]["description"].value() == data["entries-1-description"]
    assert rows[2]["starts_at"].value() == time(8, 45)
    assert rows[2]["ends_at"].value() == time(9)
    assert rows[2]["participants"].value() == [str(value) for value in data["workforce"]]
    assert workspace.reports.count() == 1
    report = workspace.reports.first()
    response = client.get(reverse("demo:report_edit", kwargs={"pk": report.pk}))
    assert len(response.context["formset"].forms) == report.entries.count()


def test_save_htmx_redirect_invalid_grid_errors_and_order(client, demo_editor):
    workspace, data = demo_editor
    data["entries-1-work_type"] = data["entries-0-work_type"]
    data["entries-1-quantity"] = "1"
    data["entries-0-starts_at"] = "07:05"
    response = client.post(reverse("demo:report_new"), {**data, "action": "save"}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert "data-error-toast" in response.content.decode()
    assert workspace.reports.count() == 1
    data["entries-0-starts_at"] = "07:00"
    response = client.post(reverse("demo:report_new"), {**data, "action": "move:1:up"})
    moved = response.context["formset"]
    for row in moved:
        for field in row:
            data[field.html_name] = field.value()
    data["entries-INITIAL_FORMS"] = "2"
    response = client.post(reverse("demo:report_new"), {**data, "action": "save"}, HTTP_HX_REQUEST="true")
    report = workspace.reports.order_by("-pk").first()
    assert response.headers["HX-Redirect"] == reverse("demo:report_detail", kwargs={"pk": report.pk})
    assert list(report.entries.values_list("description", flat=True)) == [
        "Unvollständige zweite Arbeit",
        "Erste Arbeit",
    ]


def test_structural_actions_preserve_edit_version_and_enforce_card_limit(client, demo_editor):
    workspace, data = demo_editor
    report = workspace.reports.first()
    data["version"] = "1"
    response = client.post(reverse("demo:report_edit", kwargs={"pk": report.pk}), {**data, "action": "add"})
    assert response.context["form"]["version"].value() == "1"
    report.refresh_from_db()
    assert report.version == 1
    data["entries-TOTAL_FORMS"] = "100"
    response = client.post(reverse("demo:report_new"), {**data, "action": "add"})
    assert len(response.context["formset"].forms) == 100
