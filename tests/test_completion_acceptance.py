"""DLC-Abschluss übergibt Standorte atomar an die Kundenabnahme."""

from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from features.customer_portal.models import CustomerAuditEvent, SiteReview
from features.customer_portal.services import decide_review, grant_membership, submit_for_review
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, Client, ProjectGroup
from features.projects.services import save_object, set_site_status

pytestmark = pytest.mark.django_db


@pytest.fixture
def ready_site():
    users = get_user_model()
    manager = users.objects.create_superuser(username="completion-manager", password=None)
    customer = users.objects.create_user(username="completion-customer")
    client = Client.objects.create(name="MBG")
    grant_membership(actor=manager, user=customer, client=client)
    group = ProjectGroup.objects.create(name="Anlage", client=client)
    site = AcObject.objects.create(group=group, name="Standort", status="started")
    report = MbgDailyReport.objects.create(
        author=manager,
        site=site,
        work_date=date(2026, 10, 3),
        status="accepted",
        version=1,
        submission_key=uuid4(),
    )
    MbgReportRevision.objects.create(
        report=report,
        actor=manager,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "entries": [
                {
                    "work_type_code": "cable",
                    "description": "Kabel verlegen",
                    "unit": "m",
                    "work_item_id": 1,
                    "completed_quantity": "25",
                    "quantity": "25",
                }
            ],
        },
    )
    return manager, customer, site, report


def complete(manager, site, path):
    if path == "status":
        return set_site_status(actor=manager, site=site, status="completed")
    return save_object(actor=manager, group=site.group, object_id=site.pk, data={"status": "completed"})


@pytest.mark.parametrize("path", ["status", "form"])
def test_completion_submits_customer_review_and_repeated_completion_is_idempotent(ready_site, path):
    manager, _customer, site, _report = ready_site
    complete(manager, site, path)
    review = SiteReview.objects.get(site=site)
    assert review.status == "submitted"
    assert review.submitted_by == manager
    site.refresh_from_db()
    assert site.status == "completed"
    original_submission = review.submitted_at
    complete(manager, site, path)
    review.refresh_from_db()
    assert review.submitted_at == original_submission
    assert CustomerAuditEvent.objects.filter(action="review_submitted", target_id=review.pk).count() == 1


@pytest.mark.parametrize("path", ["status", "form"])
def test_completion_failure_rolls_back_site_status_and_audit(ready_site, path):
    manager, _customer, site, report = ready_site
    report.version = 2
    report.save(update_fields=["version"])
    before = CustomerAuditEvent.objects.count()
    with pytest.raises(ValidationError):
        complete(manager, site, path)
    site.refresh_from_db()
    assert site.status == "started"
    assert not SiteReview.objects.filter(site=site).exists()
    assert CustomerAuditEvent.objects.count() == before


def test_repeated_completion_preserves_customer_acceptance(ready_site):
    manager, customer, site, _report = ready_site
    complete(manager, site, "status")
    review = decide_review(actor=customer, site=site, **review_decisions(site))
    original_decision = review.decided_at
    complete(manager, site, "form")
    review.refresh_from_db()
    assert (review.status, review.decided_by, review.decided_at) == ("accepted", customer, original_decision)


def test_explicit_completion_resubmits_returned_review(ready_site):
    manager, customer, site, _report = ready_site
    complete(manager, site, "status")
    review = decide_review(actor=customer, site=site, **review_decisions(site, rejected="Bitte prüfen"))
    complete(manager, site, "status")
    review.refresh_from_db()
    assert review.status == "submitted"
    assert review.decided_by is None
    assert review.remark == ""


def test_repeated_completed_status_repairs_missing_submission(ready_site):
    manager, _customer, site, _report = ready_site
    site.status = "completed"
    site.save(update_fields=["status"])
    complete(manager, site, "status")
    assert SiteReview.objects.get(site=site).status == "submitted"


def test_inactive_client_completion_rolls_back(ready_site):
    manager, _customer, site, _report = ready_site
    client = site.group.client
    client.is_active = False
    client.save(update_fields=["is_active"])
    with pytest.raises(ValidationError):
        complete(manager, site, "status")
    site.refresh_from_db()
    assert site.status == "started"


def test_completed_site_without_daily_reports_can_be_submitted():
    manager = get_user_model().objects.create_superuser(username="no-reports-manager", password=None)
    group = ProjectGroup.objects.create(name="Anlage", client=Client.objects.create(name="MBG"))
    site = AcObject.objects.create(group=group, name="Standort", status="started")
    complete(manager, site, "status")
    assert SiteReview.objects.get(site=site).status == "submitted"
    assert not MbgDailyReport.objects.filter(site=site).exists()


def test_incomplete_site_without_accepted_reports_cannot_be_submitted():
    manager = get_user_model().objects.create_superuser(username="unfinished-manager", password=None)
    group = ProjectGroup.objects.create(name="Anlage", client=Client.objects.create(name="MBG"))
    site = AcObject.objects.create(group=group, name="Standort", status="started")
    with pytest.raises(ValidationError):
        submit_for_review(actor=manager, site=site)
    assert not SiteReview.objects.filter(site=site).exists()


def test_unrelated_edit_preserves_returned_review(ready_site):
    manager, customer, site, _report = ready_site
    complete(manager, site, "status")
    review = decide_review(actor=customer, site=site, **review_decisions(site, rejected="Bitte prüfen"))
    save_object(actor=manager, group=site.group, object_id=site.pk, data={"name": "Neuer Name"})
    review.refresh_from_db()
    assert review.status == "returned"
    assert review.remark == "Kabel verlegen: Bitte prüfen"


def review_decisions(site, rejected=None):
    review = SiteReview.objects.get(site=site)
    return {
        "snapshot_digest": review.snapshot_digest,
        "submission_token": review.submitted_at.isoformat(),
        "decisions": {
            row["key"]: {"decision": "accepted" if rejected is None else "rejected", "comment": rejected or ""}
            for row in review.work_snapshot
        },
    }
