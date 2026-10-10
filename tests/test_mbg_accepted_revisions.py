"""Tests for unified accepted current revision loading across reporting and exports."""

import json
from datetime import date, time
from decimal import Decimal
from hashlib import sha256
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from features.mbg_reports.accepted_revisions import (
    load_accepted_current_revisions,
)
from features.mbg_reports.exports import generate_final_hours, generate_week
from features.mbg_reports.models import (
    CURRENT_WEEKLY_EXPORT_TEMPLATE,
    FinalHourlyExport,
    MbgDailyReport,
    MbgReportRevision,
    WeeklyExport,
)
from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    admin = get_user_model().objects.create_user(username="rev-admin", is_superuser=True)
    employee = Employee.objects.create(first_name="Hans", last_name="Bauer", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Solarpark West", has_ac=True, status="active")
    site = AcObject.objects.create(
        group=group,
        name="Station A",
        address="Feldweg 12",
        project_number="P-5501",
        status="in_progress",
        is_active=True,
    )
    work = WorkType.objects.get(code="wr-montage")
    entry = {
        "participants": [employee],
        "starts_at": time(8),
        "ends_at": time(12),
        "work_type": work,
        "quantity": Decimal("2"),
        "cable_type": None,
        "route": None,
        "standard_connections": 0,
        "heavy_connections": 0,
        "with_underconstruction": False,
        "description": "WR Montage Test",
    }
    return admin, employee, group, site, entry


def test_loader_rejects_missing_revision_with_validation_error(setup_data):
    admin, _employee, group, site, _entry = setup_data
    target_date = date.fromisocalendar(2026, 38, 2)
    # Accepted report with version 2, but no revision exists
    report = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=target_date,
        status="accepted",
        version=2,
    )

    # 1. Direct loader check
    with pytest.raises(ValidationError, match="Отсутствует сохранённая ревизия"):
        load_accepted_current_revisions([report], strict=True)

    non_strict_batch = load_accepted_current_revisions([report], strict=False)
    assert report.pk in non_strict_batch.excluded_report_ids
    assert len(non_strict_batch.items) == 0

    # 2. generate_week must raise ValidationError, NOT RelatedObjectDoesNotExist / DoesNotExist
    with pytest.raises(ValidationError):
        generate_week(actor=admin, year=2026, week=38)

    # 3. generate_final_hours must raise ValidationError
    site.status = "completed"
    site.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        generate_final_hours(actor=admin, group_id=group.pk)

    # 4. load_accepted_reports_dataset excludes the corrupted report
    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    assert report.pk in dataset.excluded_report_ids


def test_loader_rejects_snapshot_status_mismatch_with_validation_error(setup_data):
    admin, _employee, group, site, _entry = setup_data
    target_date = date.fromisocalendar(2026, 38, 3)
    report = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=target_date,
        status="accepted",
        version=1,
    )
    # Revision snapshot status is "draft" instead of "accepted"
    MbgReportRevision.objects.create(
        report=report,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "draft",
            "site_id": site.pk,
            "site_name": site.name,
            "address": site.address,
            "project_number": site.project_number,
            "group_name": group.name,
            "date": str(target_date),
            "entries": [],
        },
    )

    # 1. Direct loader check
    with pytest.raises(ValidationError, match="не находится в статусе accepted"):
        load_accepted_current_revisions([report], strict=True)

    # 2. generate_week must reject snapshot status mismatch
    with pytest.raises(ValidationError):
        generate_week(actor=admin, year=2026, week=38)

    # 3. generate_final_hours must reject snapshot status mismatch
    site.status = "completed"
    site.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        generate_final_hours(actor=admin, group_id=group.pk)

    # 4. load_accepted_reports_dataset excludes it
    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    assert report.pk in dataset.excluded_report_ids


def test_strict_draft_rejection(setup_data):
    admin, employee, group, site, entry = setup_data
    target_date = date.fromisocalendar(2026, 38, 4)
    report = save_report(
        actor=admin,
        site=site,
        work_date=target_date,
        workforce=[employee],
        entries=[entry],
        submit=False,
    )
    assert report.status == "draft"

    with pytest.raises(ValidationError, match=r"Отчёт .* не утверждён"):
        load_accepted_current_revisions([report], strict=True)

    with pytest.raises(ValidationError, match="Для выгрузки нужны принятые отчёты"):
        generate_week(actor=admin, year=2026, week=38)

    site.status = "completed"
    site.save(update_fields=["status"])
    with pytest.raises(ValidationError, match="все отчёты проекта должны быть приняты"):
        generate_final_hours(actor=admin, group_id=group.pk)


def test_shared_runtime_and_batch_querying(setup_data, monkeypatch, tmp_path):
    monkeypatch.setattr(WeeklyExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    monkeypatch.setattr(FinalHourlyExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin, employee, group, site, entry = setup_data
    target_date = date.fromisocalendar(2026, 38, 5)
    report = save_report(
        actor=admin,
        site=site,
        work_date=target_date,
        workforce=[employee],
        entries=[entry],
        submit=True,
    )
    review_report(actor=admin, report_id=report.pk, version=1, decision="accept")

    # Spy on load_accepted_current_revisions to verify it is called by both hourly generators and dataset selector
    with patch(
        "features.mbg_reports.accepted_revisions.load_accepted_current_revisions",
        wraps=load_accepted_current_revisions,
    ) as spy_loader:
        # Weekly
        weekly_artifact = generate_week(actor=admin, year=2026, week=38)
        assert spy_loader.call_count == 1
        assert weekly_artifact is not None

        # Final hours
        site.status = "completed"
        site.save(update_fields=["status"])
        final_artifact = generate_final_hours(actor=admin, group_id=group.pk)
        assert spy_loader.call_count == 2
        assert final_artifact is not None

        # Dataset selector
        dataset = load_accepted_reports_dataset(site_ids=[site.pk])
        assert spy_loader.call_count == 3
        assert len(dataset.all_sites[site.pk].day_facts) == 1


def test_preserved_identical_fingerprint_and_artifact_reuse(setup_data, monkeypatch, tmp_path):
    monkeypatch.setattr(WeeklyExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    monkeypatch.setattr(FinalHourlyExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin, employee, group, site, entry = setup_data
    target_date = date.fromisocalendar(2026, 38, 5)
    report = save_report(
        actor=admin,
        site=site,
        work_date=target_date,
        workforce=[employee],
        entries=[entry],
        submit=True,
    )
    review_report(actor=admin, report_id=report.pk, version=1, decision="accept")

    # Weekly export
    report.refresh_from_db()
    accepted_snapshot = report.revisions.get(version=report.version).snapshot
    original_fingerprint = sha256(
        json.dumps(
            {
                "template": CURRENT_WEEKLY_EXPORT_TEMPLATE,
                "year": 2026,
                "week": 38,
                "reports": [(report.pk, report.version)],
                "data": [accepted_snapshot],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    art_w1 = generate_week(actor=admin, year=2026, week=38)
    art_w2 = generate_week(actor=admin, year=2026, week=38)
    assert art_w1.pk == art_w2.pk
    assert art_w1.fingerprint == art_w2.fingerprint
    assert art_w1.fingerprint == original_fingerprint
    assert art_w1.snapshot == [accepted_snapshot]
    assert isinstance(art_w1.snapshot, list)
    assert art_w1.snapshot[0]["status"] == "accepted"

    # Final hourly export
    site.status = "completed"
    site.save(update_fields=["status"])
    art_f1 = generate_final_hours(actor=admin, group_id=group.pk)
    art_f2 = generate_final_hours(actor=admin, group_id=group.pk)
    assert art_f1.pk == art_f2.pk
    assert art_f1.fingerprint == art_f2.fingerprint
    assert isinstance(art_f1.snapshot, dict)
    assert isinstance(art_f1.snapshot["reports"], list)
    assert art_f1.snapshot["reports"][0]["status"] == "accepted"


def test_batch_preserves_input_order_with_one_revision_query(setup_data, django_assert_num_queries):
    admin, _employee, _group, site, _entry = setup_data
    reports = []
    for day in (14, 15):
        report = MbgDailyReport.objects.create(
            site=site, author=admin, work_date=date(2026, 9, day), status="accepted", version=1
        )
        MbgReportRevision.objects.create(
            report=report,
            actor=admin,
            version=1,
            action="accept",
            snapshot={"status": "accepted", "marker": day, "quantity": None},
        )
        reports.append(report)
    with django_assert_num_queries(1):
        batch = load_accepted_current_revisions(list(reversed(reports)), strict=True)
    assert [report.pk for report, _snapshot in batch.items] == [reports[1].pk, reports[0].pk]
    assert [snapshot["marker"] for snapshot in batch.snapshots] == [15, 14]
    assert all(snapshot["quantity"] is None for snapshot in batch.snapshots)
