"""Accepted physical quantities close planned work independently of customer review."""

from datetime import time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from features.customer_portal.selectors import attach_site_plan_progress
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.projects.read_models import site_work_plan
from features.projects.services import save_site_work_item, set_site_status, set_work_item_lifecycle
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def planned_site():
    manager = get_user_model().objects.create_user(username="readiness-manager", is_superuser=True)
    worker = Employee.objects.create(first_name="Readiness", last_name="Worker", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Readiness")
    site = AcObject.objects.create(group=group, name="Haus 1")
    work = WorkType.objects.create(
        code="readiness-wr", name_de="Montage Wechselrichter", direction="ac", unit="piece",
        calculation_rule="fixed", price_mode="per_unit",
    )
    item = save_site_work_item(actor=manager, site=site, work_type=work, label="WR 1", planned_quantity=2)
    return manager, worker, site, work, item


def accept_one(manager, worker, site, work, item, *, delta=Decimal("1")):
    report = save_report(
        actor=manager, site=site, work_date=timezone.localdate(), workforce=[worker], submit=True,
        entries=[{
            "participants": [worker], "starts_at": time(8), "ends_at": time(9),
            "work_type": work, "quantity": Decimal("1"), "description": "WR 1",
            "work_item": item, "completed_quantity": delta,
        }],
    )
    review_report(actor=manager, report_id=report.pk, version=report.version, decision="accept")
    report.refresh_from_db()
    return report


def replan(manager, site, work, item, quantity):
    return save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR 1", planned_quantity=quantity, work_item_id=item.pk,
    )


def test_explicit_completion_and_plan_guard(planned_site):
    manager, worker, site, work, item = planned_site
    assert site_work_plan(site).rows[0].status == "not_started"
    assert site_work_plan(site).rows[0].remaining_quantity == Decimal("2")
    with pytest.raises(ValidationError):
        set_site_status(actor=manager, site=site, status="completed")
    report = accept_one(manager, worker, site, work, item)
    assert site_work_plan(site).rows[0].status == "partial"
    with pytest.raises(ValidationError):
        set_work_item_lifecycle(actor=manager, item=item, action="confirm")
    replan(manager, site, work, item, 1)
    assert site_work_plan(site).rows[0].status == "completed"
    assert site_work_plan(site).is_ready is True
    set_site_status(actor=manager, site=site, status="completed")
    replan(manager, site, work, item, 2)
    site.refresh_from_db()
    assert site.status == "completed"  # readiness changed, historic completion is not auto-reopened
    assert site_work_plan(site).is_ready is False
    assert report.revisions.count() == 2


def test_readiness_rechecks_plan_and_accepted_report(planned_site):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item)
    replan(manager, site, work, item, 1)
    replan(manager, site, work, item, 2)
    assert site_work_plan(site).is_ready is False
    replan(manager, site, work, item, 1)
    report.status = "returned"
    report.save(update_fields=["status"])
    assert site_work_plan(site).is_ready is False


def test_zero_delta_with_accepted_hours_is_partial_not_complete(planned_site):
    manager, worker, site, work, item = planned_site
    accept_one(manager, worker, site, work, item, delta=Decimal("0"))
    assert site_work_plan(site).rows[0].status == "partial"
    assert site_work_plan(site).rows[0].remaining_quantity == Decimal("2")
    assert site_work_plan(site).is_ready is False


def test_full_accepted_quantity_closes_without_manual_or_customer_confirmation(planned_site):
    manager, worker, site, work, item = planned_site
    accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    item.refresh_from_db()
    assert item.completion_confirmed_at is None
    assert site_work_plan(site).rows[0].status == "completed"
    assert site_work_plan(site).is_ready is True
    attach_site_plan_progress([site])
    assert site.plan_progress == "1/1"
    assert site.plan_progress_percent == 100
    assert not hasattr(site, "customer_review")


def test_auto_completion_reopens_after_plan_increase_or_report_revocation(planned_site):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    replan(manager, site, work, item, 3)
    assert site_work_plan(site).rows[0].status == "partial"
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"
    replan(manager, site, work, item, 2)
    assert site_work_plan(site).rows[0].status == "completed"
    report.status = "returned"
    report.save(update_fields=["status"])
    assert site_work_plan(site).rows[0].status == "not_started"
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


def test_obsolete_accepted_snapshot_does_not_close_current_report(planned_site):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    report.version += 1
    report.save(update_fields=["version"])
    overview = site_work_plan(site)
    assert overview.rows[0].status == "not_started"
    assert overview.excluded_report_count == 1
    assert overview.is_ready is False
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


@pytest.mark.parametrize("status", ["draft", "submitted"])
def test_unaccepted_report_does_not_close_planned_work(planned_site, status):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    report.status = status
    report.save(update_fields=["status"])
    assert site_work_plan(site).rows[0].status == "not_started"
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


def test_missing_physical_delta_cannot_close_work_from_accepted_hours(planned_site):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    revision = report.revisions.get(version=report.version)
    revision.snapshot["entries"][0]["completed_quantity"] = None
    revision.save(update_fields=["snapshot"])
    overview = site_work_plan(site)
    assert overview.rows[0].status == "not_started"
    assert overview.unresolved_count == 1
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


def test_customer_progress_excludes_internal_only_accepted_work(planned_site):
    manager, worker, site, work, item = planned_site
    report = accept_one(manager, worker, site, work, item, delta=Decimal("2"))
    revision = report.revisions.get(version=report.version)
    revision.snapshot["entries"][0]["internal_only"] = True
    revision.save(update_fields=["snapshot"])
    assert site_work_plan(site).rows[0].status == "completed"
    assert site_work_plan(site, include_internal=False).rows[0].status == "not_started"
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


def test_zero_plan_never_closes_from_hours_or_no_evidence(planned_site):
    _manager, _worker, site, _work, item = planned_site
    from features.projects.read_models import PlannedWorkRow

    item.planned_quantity = Decimal("0")
    assert PlannedWorkRow(item, Decimal("0"), Decimal("0")).status == "not_started"
    assert PlannedWorkRow(item, Decimal("0"), Decimal("1")).status == "partial"
    attach_site_plan_progress([site])
    assert site.plan_progress == "0/1"


def test_not_required_reason_permissions_and_legacy_no_plan(planned_site):
    manager, worker, site, work, item = planned_site
    accept_one(manager, worker, site, work, item)
    ordinary = get_user_model().objects.create_user(username="readiness-ordinary")
    with pytest.raises(PermissionDenied):
        set_work_item_lifecycle(actor=ordinary, item=item, action="not_required", reason="Nicht nötig")
    with pytest.raises(ValidationError):
        set_work_item_lifecycle(actor=manager, item=item, action="not_required", reason="")
    set_work_item_lifecycle(actor=manager, item=item, action="not_required", reason="Technisch nicht nötig")
    assert site_work_plan(site).rows[0].status == "not_required"
    assert site_work_plan(site).rows[0].completed_quantity == 1
    assert site_work_plan(site).is_ready is True
    set_work_item_lifecycle(actor=manager, item=item, action="reopen")
    assert site_work_plan(site).is_ready is False
    legacy = AcObject.objects.create(group=site.group, name="Haus ohne Plan")
    assert site_work_plan(legacy).is_ready is None
    set_site_status(actor=manager, site=legacy, status="completed")


def test_http_status_guard_and_manager_item_controls(planned_site, client):
    manager, _worker, site, _work, item = planned_site
    client.force_login(manager)
    status_url = reverse("projects:site_status", args=[site.group_id, site.pk])
    action_url = reverse("projects:work_item_lifecycle", args=[site.group_id, site.pk, item.pk])
    assert client.post(status_url, {"status": "completed"}).status_code == 302
    site.refresh_from_db()
    assert site.status != "completed"
    page = client.get(reverse("projects:site_detail", args=[site.group_id, site.pk]))
    assert page.status_code == 200
    assert "Осталось" in page.content.decode()
    form_url = reverse("projects:object_edit", args=[site.group_id, site.pk])
    form_response = client.post(form_url, {
        "name": site.name, "address": site.address, "project_number": site.project_number,
        "status": "completed", "is_active": "on",
    })
    assert form_response.status_code == 200
    site.refresh_from_db()
    assert site.status != "completed"
    assert client.post(action_url, {"action": "not_required", "reason": "Nicht vorgesehen"}).status_code == 302
    assert client.post(status_url, {"status": "completed"}).status_code == 302
    site.refresh_from_db()
    assert site.status == "completed"
    ordinary = get_user_model().objects.create_user(username="readiness-viewer")
    client.force_login(ordinary)
    assert client.post(action_url, {"action": "reopen"}).status_code == 403
