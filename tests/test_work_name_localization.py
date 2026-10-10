# ruff: noqa: RUF001
"""Stored bilingual names localize reads without changing acceptance evidence."""

from copy import deepcopy
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils.translation import override
from features.customer_portal.selectors import accepted_completion_rows, accepted_daily_work
from features.customer_portal.services import accepted_snapshot_digest, review_work_snapshot
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.read_models import site_work_plan
from features.work_catalog.localization import WorkNameResolver
from features.work_catalog.models import WorkDescriptionTranslation, WorkType

pytestmark = pytest.mark.django_db


def test_report_and_review_names_use_database_language_without_changing_sources():
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Anlage"), name="Haus")
    actor = get_user_model().objects.create_user(username="localizer")
    report = MbgDailyReport.objects.create(author=actor, site=site, work_date=date(2026, 10, 10), status="accepted")
    original = {
        "status": "accepted",
        "entries": [{"description": "Eigene Arbeit", "quantity": "1", "unit": "hour", "actual_person_hours": "0.25"}],
    }
    revision = MbgReportRevision.objects.create(
        actor=actor,
        report=report,
        version=report.version,
        action="accepted",
        reason="test",
        snapshot=deepcopy(original),
    )
    WorkDescriptionTranslation.objects.create(
        original="Eigene Arbeit", name_de="Eigene Arbeit", name_ru="Отдельная работа"
    )
    digest = accepted_snapshot_digest(site)
    with override("ru"):
        assert accepted_daily_work(site)[0].description == "Отдельная работа"
        assert accepted_completion_rows(site)[0].name == "Отдельная работа"
        ru_snapshot = review_work_snapshot(site)
    with override("de"):
        assert accepted_completion_rows(site)[0].name == "Eigene Arbeit"
        assert review_work_snapshot(site) == ru_snapshot
    assert ru_snapshot[0]["name_ru"] == "Отдельная работа"
    assert ru_snapshot[0]["sources"][0]["description"] == "Eigene Arbeit"
    assert accepted_snapshot_digest(site) == digest
    revision.refresh_from_db()
    assert revision.snapshot == original


def test_custom_plan_label_and_composed_catalog_names_are_localized():
    work = WorkType.objects.create(code="test-localized", name_de="Montage Gerät", name_ru="Монтаж устройства")
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Anlage"), name="Haus")
    SiteWorkItem.objects.create(
        site=site, work_type=work, label="Montage Gerät · 5×16 mm²", planned_quantity=1, unit_snapshot="piece"
    )
    with override("ru"):
        assert site_work_plan(site).rows[0].name == "Монтаж устройства · 5×16 mm²"
    with override("de"):
        assert site_work_plan(site).rows[0].name == "Montage Gerät · 5×16 mm²"


def test_stored_review_names_remain_immutable_when_translation_changes():
    WorkDescriptionTranslation.objects.create(original="Eigen", name_de="Eigen", name_ru="Первый")
    row = {"name": "Eigen", "name_de": "Eigen", "name_ru": "Зафиксированный", "route": "", "cable_type": ""}
    with override("ru"):
        assert WorkNameResolver().snapshot_row(row)["name"] == "Зафиксированный"
    assert row["name"] == "Eigen"


def test_translation_import_dry_run_and_permissions_preserve_manual_names():
    from io import StringIO

    from django.core.management import call_command
    from django.core.management.base import CommandError

    WorkDescriptionTranslation.objects.create(
        original="Montage Wechselrichter", name_de="Montage Wechselrichter", name_ru="Ручной перевод"
    )
    before = WorkDescriptionTranslation.objects.count()
    call_command("populate_work_name_translations", stdout=StringIO())
    assert WorkDescriptionTranslation.objects.count() == before
    with pytest.raises(CommandError):
        call_command("populate_work_name_translations", apply=True, actor="missing", stdout=StringIO())
    manager = get_user_model().objects.create_superuser(
        username="translation-manager", email="m@example.test", password=None
    )
    call_command("populate_work_name_translations", apply=True, actor=manager.username, stdout=StringIO())
    assert WorkDescriptionTranslation.objects.get(original="Montage Wechselrichter").name_ru == "Ручной перевод"
    assert WorkDescriptionTranslation.objects.count() > before


@pytest.mark.parametrize("status", ["accepted", "returned"])
def test_historical_review_read_keeps_decisions_and_original_snapshot(status):
    from features.customer_portal.models import SiteReview
    from features.customer_portal.selectors import customer_site_detail

    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Anlage"), name="Haus")
    original = [{"key": "1", "name": "Eigene Arbeit", "unit": "piece", "quantity": "1", "route": "", "cable_type": ""}]
    decisions = {"1": {"decision": "rejected", "comment": "Bestehender Kommentar"}}
    review = SiteReview.objects.create(
        site=site, status=status, work_snapshot=deepcopy(original), item_decisions=deepcopy(decisions)
    )
    WorkDescriptionTranslation.objects.create(
        original="Eigene Arbeit", name_de="Eigene Arbeit", name_ru="Отдельная работа"
    )
    with override("ru"):
        assert customer_site_detail(site).review_rows[0]["name"] == "Отдельная работа"
    review.refresh_from_db()
    assert review.work_snapshot == original
    assert review.item_decisions == decisions
    assert review.status == status
