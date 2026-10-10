"""Internal-only work remains visible to DLC while customer views hide it."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from features.customer_portal.selectors import accepted_daily_work
from features.mbg_reports.selectors import weekly_export_cards
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.projects.read_models import internal_daily_work, site_activity
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


def test_internal_project_history_and_hours_retain_hidden_work(client):
    actor = get_user_model().objects.create_superuser(username="internal-visibility", password=None)
    employee = Employee.objects.create(first_name="Test", last_name="Worker", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Internal visibility", has_ac=True, status="active")
    site = AcObject.objects.create(group=group, name="Site", address="Test address", project_number="P-1")
    work = WorkType.objects.get(code="sonstige")
    base = {"participants": [employee], "work_type": work, "quantity": Decimal("1")}
    report = save_report(
        actor=actor,
        site=site,
        work_date=date(2026, 10, 9),
        workforce=[employee],
        submit=True,
        entries=[
            {
                **base,
                "starts_at": time(8),
                "ends_at": time(9),
                "description": "Private mortar address",
                "internal_only": True,
            },
            {
                **base,
                "starts_at": time(9),
                "ends_at": time(10),
                "description": "Visible physical work",
                "internal_only": False,
            },
        ],
    )
    review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
    rows = internal_daily_work(site)
    assert [row["internal_only"] for row in rows] == [True, False]
    assert sum(row["actual_person_hours"] for row in rows) == Decimal("2")
    activity = site_activity(site)
    assert activity.recorded_person_hours == Decimal("2")
    assert activity.accepted_person_hours == Decimal("2")
    assert weekly_export_cards()[0].person_hours == Decimal("2")
    assert [row.description for row in accepted_daily_work(site)] == ["Visible physical work"]
    client.force_login(actor)
    page = client.get(reverse("projects:site_detail", args=[group.pk, site.pk]))
    assert page.status_code == 200
    assert "Private mortar address" in page.content.decode()
    assert "Только внутренний учёт" in page.content.decode()
