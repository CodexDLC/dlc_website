"""Real database locks require PostgreSQL; SQLite cannot verify this contract."""

from concurrent.futures import ThreadPoolExecutor
from datetime import time
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.utils import timezone
from features.mbg_reports.models import MbgDailyReport
from features.mbg_reports.services import save_report
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import WorkType


@pytest.mark.django_db(transaction=True)
def test_postgres_serializes_employee_overlap():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL required to verify select_for_update")
    admin = get_user_model().objects.create_user(username="concurrency", is_superuser=True)
    employee = Employee.objects.create(first_name="Concurrent", last_name="Employee", has_ac_access=True)
    work_type, _ = WorkType.objects.get_or_create(
        code="AC_CONCURRENCY_TEST",
        defaults={"name_de": "Montage", "direction": WorkType.Direction.AC, "is_break": False},
    )
    sites = [
        AcObject.objects.create(group=ProjectGroup.objects.create(name=f"Group {i}"), name=f"House {i}")
        for i in range(2)
    ]
    barrier = Barrier(2)

    def submit(site_id):
        try:
            actor = get_user_model().objects.get(pk=admin.pk)
            person = Employee.objects.get(pk=employee.pk)
            site = AcObject.objects.get(pk=site_id)
            barrier.wait(timeout=10)
            try:
                save_report(
                    actor=actor,
                    site=site,
                    work_date=timezone.localdate(),
                    workforce=[person],
                    entries=[
                        dict(
                            participants=[person],
                            starts_at=time(9),
                            ends_at=time(10),
                            description="Montage",
                            work_type=work_type,
                            quantity=1,
                        )
                    ],
                )
                return "saved"
            except ValidationError:
                return "rejected"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [site.pk for site in sites]))
    assert sorted(results) == ["rejected", "saved"]
    assert MbgDailyReport.objects.count() == 1
