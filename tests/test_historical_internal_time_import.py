"""Импорт старых почасовых записей не создаёт дубли."""

from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from features.internal_time.historical_imports import HistoricalTeamReport, import_historical_report
from features.internal_time.models import TeamReport
from features.projects.models import ProjectGroup
from features.staff.models import Employee

pytestmark = pytest.mark.django_db


def test_historical_report_import_is_idempotent():
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    group = ProjectGroup.objects.create(name="Synthetic Project9", has_ac=True, has_dc=False)
    first = Employee.objects.create(first_name="Testperson1", last_name="Example1")
    second = Employee.objects.create(first_name="Testperson2", last_name="Example2")
    source = HistoricalTeamReport(
        source_key="synthetic-history-record10",
        work_date=date(2026, 9, 7),
        starts_at=time(7),
        ends_at=time(18),
        direction="ac",
        participant_names=("Testperson1 Example1", "Testperson2 Example2"),
        source_location="Synthetic Project9",
    )

    first_result = import_historical_report(actor=admin, group=group, source=source)
    second_result = import_historical_report(actor=admin, group=group, source=source)

    assert first_result.created is True
    assert second_result.created is False
    assert TeamReport.objects.count() == 1
    report = TeamReport.objects.get()
    assert report.status == TeamReport.Status.ACCEPTED
    assert report.lunch_minutes == 30
    assert set(report.participants.values_list("employee_id", flat=True)) == {first.pk, second.pk}


def test_historical_report_can_be_added_to_completed_group():
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    group = ProjectGroup.objects.create(
        name="Synthetic Project11",
        has_ac=True,
        has_dc=True,
        status="completed",
        dc_status="completed",
    )
    Employee.objects.create(first_name="Testperson3", last_name="Example3")
    source = HistoricalTeamReport(
        source_key="synthetic-history-record12",
        work_date=date(2026, 9, 7),
        starts_at=time(7),
        ends_at=time(18),
        direction="dc",
        participant_names=("Testperson3 Example3",),
        source_location="Example Location13",
    )

    result = import_historical_report(actor=admin, group=group, source=source)

    group.refresh_from_db()
    assert result.created is True
    assert group.status == "completed"
    assert group.dc_status == "completed"
