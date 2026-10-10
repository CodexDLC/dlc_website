"""Internal-only rows retain DLC time but never enter customer documents."""

from copy import deepcopy
from datetime import date, time
from decimal import Decimal
from io import BytesIO

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from features.customer_portal.selectors import accepted_completion_rows, accepted_daily_work
from features.mbg_reports.completion_projection import project_accepted_entries
from features.mbg_reports.export_services import (
    generate_site_performance_report,
    generate_week,
    generate_work_completion_report,
)
from features.mbg_reports.models import PerformanceExport, WeeklyExport
from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.services import review_report, save_report
from features.mbg_reports.work_items import accepted_work_item_progress
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def mixed():
    actor = get_user_model().objects.create_superuser(username="internal-owner", password=None)
    employee = Employee.objects.create(first_name="Test", last_name="Worker", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Internal mix", has_ac=True, status="active")
    site = AcObject.objects.create(group=group, name="Site", address="Test address", project_number="P-1")
    work = WorkType.objects.get(code="sonstige")
    base = dict(participants=[employee], work_type=work, quantity=Decimal("1"))
    rows = [
        dict(base, starts_at=time(8), ends_at=time(9), description="Private mortar addresses", internal_only=True),
        dict(base, starts_at=time(9), ends_at=time(10), description="Visible zero-priced work"),
    ]
    report = save_report(
        actor=actor, site=site, work_date=date(2026, 10, 9), workforce=[employee], entries=rows, submit=True
    )
    report = review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
    return actor, employee, group, site, report, rows


def test_snapshot_flag_and_hours_are_independent(mixed):
    _, _, _, site, report, _ = mixed
    snapshot = report.revisions.get(version=report.version).snapshot
    assert [e["internal_only"] for e in snapshot["entries"]] == [True, False]
    data = load_accepted_reports_dataset(site_ids=[site.pk]).all_sites[site.pk]
    assert data.day_facts[0].total_hours == Decimal("2")
    assert len(data.day_facts[0].entries) == 2
    assert [r.name for r in data.position_rows] == ["Visible zero-priced work"]
    assert [r.description for r in accepted_daily_work(site)] == ["Visible zero-priced work"]
    assert [r.name for r in accepted_completion_rows(site)] == ["Visible zero-priced work"]


def test_historical_snapshot_without_flag_is_not_excluded(mixed):
    _, _, _, _, report, _ = mixed
    snapshot = deepcopy(report.revisions.get(version=report.version).snapshot)
    for e in snapshot["entries"]:
        e.pop("internal_only")
    result = project_accepted_entries([(report.pk, report.version, report.work_date, snapshot)])
    assert {r.name for r in result} == {"Private mortar addresses", "Visible zero-priced work"}


def test_actual_documents_exclude_private_rows_and_weekly_time_retains_them(mixed, tmp_path, monkeypatch):
    actor, _, _, site, _, _ = mixed
    storage = FileSystemStorage(location=tmp_path)
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", storage)
    monkeypatch.setattr(WeeklyExport._meta.get_field("file"), "storage", storage)
    for artifact in [
        generate_site_performance_report(actor=actor, site_id=site.pk, is_preliminary=True),
        generate_work_completion_report(actor=actor, site_id=site.pk),
    ]:
        with artifact.file.open("rb") as f:
            wb = openpyxl.load_workbook(BytesIO(f.read()))
        text = " ".join(str(c.value) for sheet in wb for row in sheet for c in row if c.value is not None)
        assert "Private mortar addresses" not in text
        assert "Visible zero-priced work" in text
    week = generate_week(actor=actor, year=2026, week=41)
    assert "Private mortar addresses" in str(week.snapshot)


def test_internal_linked_volume_does_not_leak_into_customer_totals(mixed):
    actor, employee, _group, site, report, rows = mixed
    work = WorkType.objects.get(code="wr-montage")
    item = SiteWorkItem.objects.create(
        site=site, work_type=work, label="WR", planned_quantity=Decimal("2"), unit_snapshot="Stk."
    )
    for r in rows:
        r.update(work_type=work, work_item=item, completed_quantity=Decimal("1"))
    report = save_report(
        actor=actor,
        site=site,
        work_date=report.work_date,
        workforce=[employee],
        entries=rows,
        report_id=report.pk,
        version=report.version,
        reason="Link physical volumes",
    )
    assert accepted_work_item_progress(site_id=site.pk).items[0].completed_quantity == Decimal("2")
    visible = accepted_completion_rows(site)
    assert len(visible) == 1 and visible[0].quantity == Decimal("1")
    from features.customer_portal.selectors import customer_site_detail

    assert customer_site_detail(site).plan.rows[0].completed_quantity == Decimal("1")


def test_editor_keeps_flag_on_get_add_and_save_and_new_revision(mixed, client):
    actor, _, _, _, report, _ = mixed
    previous = deepcopy(report.revisions.get(version=report.version).snapshot)
    client.force_login(actor)
    url = reverse("mbg_reports:edit", args=[report.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["formset"].forms[0]["internal_only"].value() is True
    assert 'name="entries-0-internal_only"' in response.content.decode()
    form = response.context["form"]
    fs = response.context["formset"]
    data = {field.html_name: field.value() if field.value() is not None else "" for field in form}
    data.update(
        {
            "action": "add",
            "entries-TOTAL_FORMS": "2",
            "entries-INITIAL_FORMS": "0",
            "entries-MIN_NUM_FORMS": "1",
            "entries-MAX_NUM_FORMS": "100",
        }
    )
    for ef in fs:
        for field in ef:
            value = field.value()
            if value is not None and value is not False:
                data[field.html_name] = value
    added = client.post(url, data)
    assert added.status_code == 200
    assert "checked" in str(added.context["formset"].forms[0]["internal_only"])
    data["action"] = "save"
    data["reason"] = "Keep internal flag on edit"
    saved = client.post(url, data)
    assert saved.status_code == 302
    report.refresh_from_db()
    assert report.entries.first().internal_only
    assert report.revisions.get(version=report.version).snapshot["entries"][0]["internal_only"]
    assert report.revisions.get(version=report.version - 1).snapshot == previous
