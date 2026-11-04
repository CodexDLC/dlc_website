"""Попозиционная приёмка: полнота, замечания, снимки, права и HTTP."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from features.customer_portal.models import CustomerAuditEvent
from features.customer_portal.services import (
    backfill_review_snapshot,
    decide_review,
    grant_membership,
    submit_for_review,
)
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, Client, ProjectGroup

pytestmark = pytest.mark.django_db


@pytest.fixture
def submitted():
    users = get_user_model()
    manager = users.objects.create_superuser(username="item-manager", password=None)
    customer = users.objects.create_user(username="item-customer")
    other = users.objects.create_user(username="item-other")
    client = Client.objects.create(name="MBG")
    grant_membership(actor=manager, user=customer, client=client)
    grant_membership(actor=manager, user=other, client=Client.objects.create(name="Other"))
    site = AcObject.objects.create(
        group=ProjectGroup.objects.create(name="Anlage", client=client), name="Standort", status="completed"
    )
    report = MbgDailyReport.objects.create(
        author=manager, site=site, work_date=date(2026, 10, 3), status="accepted", version=1, submission_key=uuid4()
    )
    revision = MbgReportRevision.objects.create(
        report=report,
        actor=manager,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "entries": [
                {"work_type_code": "photo-documentation", "description": "Kabel verlegen", "unit": "meter", "work_item_id": 11, "completed_quantity": "25"},
                {"work_type_code": "photo-documentation", "description": "Anschluss", "unit": "piece", "work_item_id": 12, "completed_quantity": "2"},
            ],
        },
    )
    review = submit_for_review(actor=manager, site=site)
    return manager, customer, other, site, report, revision, review


def payload(review, rejected=False):
    return {
        row["key"]: {"decision": "rejected" if rejected else "accepted", "comment": "Kabel prüfen" if rejected else ""}
        for row in review.work_snapshot
    }


def decide(customer, site, review, decisions):
    return decide_review(
        actor=customer,
        site=site,
        snapshot_digest=review.snapshot_digest,
        submission_token=review.submitted_at.isoformat(),
        decisions=decisions,
    )


def test_snapshot_and_all_accepted_are_saved_without_changing_dlc_status(submitted):
    _, customer, _, site, _, _, review = submitted
    original = deepcopy(review.work_snapshot)
    assert len(original) == 21 and original[0]["key"] == "customer:10.010"
    result = decide(customer, site, review, payload(review))
    assert result.status == "accepted" and result.decided_by == customer
    site.refresh_from_db()
    assert site.status == "completed"
    event = CustomerAuditEvent.objects.get(action="review_decided")
    assert event.after["work_snapshot"] == original
    assert event.after["item_decisions"] == result.item_decisions


def test_mixed_return_inline_comments_and_resubmit_preserves_audit(submitted):
    manager, customer, _, site, _, _, review = submitted
    data = payload(review)
    data["customer:10.020"] = {"decision": "rejected", "comment": "  Anschluss prüfen  "}
    result = decide(customer, site, review, data)
    assert result.status == "returned"
    assert result.item_decisions["customer:10.020"]["comment"] == "Anschluss prüfen"
    old_decision = deepcopy(result.item_decisions)
    new = submit_for_review(actor=manager, site=site)
    assert new.item_decisions == {} and new.status == "submitted"
    event = CustomerAuditEvent.objects.filter(action="review_submitted").latest("pk")
    assert event.before["item_decisions"] == old_decision
    assert CustomerAuditEvent.objects.get(action="review_decided").after["item_decisions"] == old_decision


@pytest.mark.parametrize("invalid", ["missing", "extra", "undecided", "blank", "long", "bad"])
def test_invalid_item_decisions_are_atomic(submitted, invalid):
    _, customer, _, site, _, _, review = submitted
    data = payload(review)
    if invalid == "missing":
        data.pop("customer:10.010")
    if invalid == "extra":
        data["999"] = data["customer:10.010"]
    if invalid == "undecided":
        data["customer:10.010"]["decision"] = ""
    if invalid == "blank":
        data["customer:10.010"] = {"decision": "rejected", "comment": "  "}
    if invalid == "long":
        data["customer:10.010"] = {"decision": "rejected", "comment": "a" * 2001}
    if invalid == "bad":
        data["customer:10.010"] = "accepted"
    before = CustomerAuditEvent.objects.count()
    with pytest.raises(ValidationError):
        decide(customer, site, review, data)
    review.refresh_from_db()
    assert review.status == "submitted" and review.item_decisions == {}
    assert CustomerAuditEvent.objects.count() == before


@pytest.mark.parametrize("role", ["manager", "other"])
def test_only_own_customer_may_decide(submitted, role):
    manager, _, other, site, _, _, review = submitted
    with pytest.raises(PermissionDenied):
        decide(manager if role == "manager" else other, site, review, payload(review))


def test_changed_reports_and_wrong_digest_cannot_accept(submitted):
    _, customer, _, site, report, _, review = submitted
    with pytest.raises(ValidationError):
        decide_review(
            actor=customer,
            site=site,
            decisions=payload(review),
            snapshot_digest="old",
            submission_token=review.submitted_at.isoformat(),
        )
    report.version = 2
    report.save(update_fields=["version"])
    with pytest.raises(ValidationError):
        decide(customer, site, review, payload(review))
    review.refresh_from_db()
    assert review.status == "submitted"


def test_empty_snapshot_cannot_fake_acceptance(submitted):
    _, customer, _, site, _, _, review = submitted
    review.work_snapshot = []
    review.save(update_fields=["work_snapshot"])
    with pytest.raises(ValidationError):
        decide(customer, site, review, {})


def test_backfill_preserves_status_dates_and_is_idempotent(submitted):
    manager, _, _, _, _, _, review = submitted
    submitted_at = review.submitted_at
    original = deepcopy(review.work_snapshot)
    review.work_snapshot = []
    review.save(update_fields=["work_snapshot"])
    with pytest.raises(ValidationError):
        backfill_review_snapshot(actor=manager, review=review)
    review.refresh_from_db()
    assert review.status == "submitted" and review.submitted_at == submitted_at
    assert review.work_snapshot == []



def test_http_validation_preserves_selected_rows_and_comments(submitted, client, monkeypatch):
    _, customer, _, site, _, _, review = submitted
    monkeypatch.setattr(
        "features.integrations.nextcloud.services.get_site_photo_summary", lambda site: {"status": "ok", "count": 0}
    )
    client.force_login(customer)
    url = reverse("customer_portal:review_decision", args=[site.pk])
    response = client.post(
        url,
        {
            "snapshot_digest": review.snapshot_digest,
            "submission_token": review.submitted_at.isoformat(),
            "decision-customer:10.010": "rejected",
            "comment-customer:10.010": "Bitte prüfen",
        },
    )
    assert response.status_code == 400
    html = response.content.decode()
    assert 'name="decision-customer:10.010" value="rejected" required checked' in html
    assert ">Bitte prüfen</textarea>" in html
    review.refresh_from_db()
    assert review.status == "submitted"
    data = {f"decision-{row['key']}": "accepted" for row in review.work_snapshot}
    data.update({"snapshot_digest": review.snapshot_digest, "submission_token": review.submitted_at.isoformat(),
                 "decision-customer:10.010": "rejected", "comment-customer:10.010": "Bitte prüfen"})
    response = client.post(url, data)
    assert response.status_code == 302
    review.refresh_from_db()
    assert review.status == "returned"


def test_http_old_all_accept_button_cannot_bypass_positions(submitted, client):
    _, customer, _, site, _, _, review = submitted
    client.force_login(customer)
    response = client.post(reverse("customer_portal:review_decision", args=[site.pk]), {"decision": "accept"})
    assert response.status_code == 400
    review.refresh_from_db()
    assert review.status == "submitted"


def test_old_tab_cannot_decide_same_works_after_resubmission(submitted):
    manager, customer, _, site, _, _, review = submitted
    old_token = review.submitted_at.isoformat()
    decide(customer, site, review, payload(review, rejected=True))
    current = submit_for_review(actor=manager, site=site)
    with pytest.raises(ValidationError):
        decide_review(
            actor=customer,
            site=site,
            decisions=payload(current),
            snapshot_digest=review.snapshot_digest,
            submission_token=old_token,
        )
    current.refresh_from_db()
    assert current.status == "submitted" and current.item_decisions == {}


def test_second_decision_cannot_overwrite_saved_acceptance(submitted):
    _, customer, _, site, _, _, review = submitted
    decide(customer, site, review, payload(review))
    with pytest.raises(ValidationError):
        decide(customer, site, review, payload(review, rejected=True))
    review.refresh_from_db()
    assert review.status == "accepted"


def test_backfill_refuses_changed_accepted_revision(submitted):
    manager, _, _, _, report, _, review = submitted
    review.work_snapshot = []
    review.save(update_fields=["work_snapshot"])
    report.version = 2
    report.save(update_fields=["version"])
    with pytest.raises(ValidationError):
        backfill_review_snapshot(actor=manager, review=review)
    review.refresh_from_db()
    assert review.work_snapshot == []


def test_refresh_legacy_review_requires_explicit_resubmission(submitted):
    from features.customer_portal.services import refresh_pending_review_snapshot

    manager, customer, _, site, _, _, review = submitted
    original_token = review.submitted_at.isoformat()
    review.work_snapshot = [{"key": "1", "name": "old", "unit": "piece", "sources": []}]
    review.save(update_fields=["work_snapshot"])
    with pytest.raises(PermissionDenied):
        refresh_pending_review_snapshot(actor=customer, review=review)
    with pytest.raises(ValidationError):
        refresh_pending_review_snapshot(actor=manager, review=review)
    updated = submit_for_review(actor=manager, site=site)
    assert updated.submitted_at.isoformat() != original_token
    with pytest.raises(ValidationError):
        decide_review(actor=customer, site=site, snapshot_digest=updated.snapshot_digest,
                      submission_token=original_token, decisions=payload(updated))


def test_refresh_rejects_decided_and_changed_customer_snapshot(submitted):
    from features.customer_portal.services import refresh_pending_review_snapshot
    from features.work_catalog.models import CustomerWorkPosition

    manager, _, _, _, _, _, review = submitted
    review.item_decisions = payload(review)
    review.save(update_fields=["item_decisions"])
    with pytest.raises(ValidationError):
        refresh_pending_review_snapshot(actor=manager, review=review)
    review.item_decisions = {}
    review.save(update_fields=["item_decisions"])
    position = CustomerWorkPosition.objects.get(code="10.010")
    position.name_de = "Changed name"
    position.save()
    with pytest.raises(ValidationError):
        refresh_pending_review_snapshot(actor=manager, review=review)


def test_refresh_command_does_not_migrate_legacy_snapshots(submitted):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    manager, _, _, _, _, _, review = submitted
    review.work_snapshot = [{"key": "1", "name": "old", "unit": "piece"}]
    review.save(update_fields=["work_snapshot"])
    before = deepcopy(review.work_snapshot)
    events = CustomerAuditEvent.objects.count()
    for apply in (False, True):
        with pytest.raises(CommandError):
            call_command("refresh_review_physical_snapshots", actor=manager.username, apply=apply)
        review.refresh_from_db()
        assert review.work_snapshot == before
        assert CustomerAuditEvent.objects.count() == events
