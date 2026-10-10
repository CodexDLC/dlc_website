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
                {"description": "Kabel verlegen", "unit": "meter", "work_item_id": 11, "completed_quantity": "25"},
                {"description": "Anschluss", "unit": "piece", "work_item_id": 12, "completed_quantity": "2"},
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
    assert [row["quantity"] for row in original] == ["25", "2"]
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
    data["2"] = {"decision": "rejected", "comment": "  Anschluss prüfen  "}
    result = decide(customer, site, review, data)
    assert result.status == "returned"
    assert result.item_decisions["2"]["comment"] == "Anschluss prüfen"
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
        data.pop("1")
    if invalid == "extra":
        data["999"] = data["1"]
    if invalid == "undecided":
        data["1"]["decision"] = ""
    if invalid == "blank":
        data["1"] = {"decision": "rejected", "comment": "  "}
    if invalid == "long":
        data["1"] = {"decision": "rejected", "comment": "a" * 2001}
    if invalid == "bad":
        data["1"] = "accepted"
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
    prepared = backfill_review_snapshot(actor=manager, review=review)
    assert prepared.status == "submitted" and prepared.submitted_at == submitted_at
    assert prepared.work_snapshot == original
    before = CustomerAuditEvent.objects.count()
    backfill_review_snapshot(actor=manager, review=review)
    assert CustomerAuditEvent.objects.count() == before


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
            "decision-1": "rejected",
            "comment-1": "Bitte prüfen",
        },
    )
    assert response.status_code == 400
    html = response.content.decode()
    assert 'name="decision-1" value="rejected" required checked' in html
    assert ">Bitte prüfen</textarea>" in html
    review.refresh_from_db()
    assert review.status == "submitted"
    response = client.post(
        url,
        {
            "snapshot_digest": review.snapshot_digest,
            "submission_token": review.submitted_at.isoformat(),
            "decision-1": "rejected",
            "comment-1": "Bitte prüfen",
            "decision-2": "accepted",
        },
    )
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


def test_refresh_pending_physical_snapshot_preserves_digest_and_invalidates_old_tab(submitted):
    from features.customer_portal.services import refresh_pending_review_snapshot

    manager, customer, _, site, _, _, review = submitted
    old_token = review.submitted_at.isoformat()
    old_digest = review.snapshot_digest
    for row in review.work_snapshot:
        for source in row["sources"]:
            source["actual_person_hours"] = "9"
    review.save(update_fields=["work_snapshot"])
    updated = refresh_pending_review_snapshot(actor=manager, review=review)
    assert updated.snapshot_digest == old_digest
    assert updated.submitted_at.isoformat() != old_token
    assert updated.item_decisions == {}
    assert all("actual_person_hours" not in s for r in updated.work_snapshot for s in r["sources"])
    with pytest.raises(ValidationError):
        decide_review(actor=customer, site=site, snapshot_digest=old_digest,
                      submission_token=old_token, decisions=payload(updated))


def test_refresh_rejects_decided_or_changed_sources_and_customer_actor(submitted):
    from features.customer_portal.services import refresh_pending_review_snapshot

    manager, customer, _, _, _, _, review = submitted
    with pytest.raises(PermissionDenied):
        refresh_pending_review_snapshot(actor=customer, review=review)
    original = deepcopy(review.work_snapshot)
    review.work_snapshot[0]["sources"][0]["entry_index"] = 999
    review.save(update_fields=["work_snapshot"])
    with pytest.raises(ValidationError):
        refresh_pending_review_snapshot(actor=manager, review=review)
    review.work_snapshot = original
    review.item_decisions = payload(review)
    review.save(update_fields=["work_snapshot", "item_decisions"])
    with pytest.raises(ValidationError):
        refresh_pending_review_snapshot(actor=manager, review=review)


def test_refresh_command_dry_run_and_apply_are_atomic(submitted):
    from io import StringIO

    from django.core.management import call_command

    manager, _, _, _, _, _, review = submitted
    review.work_snapshot[0]["sources"][0]["actual_person_hours"] = "9"
    review.save(update_fields=["work_snapshot"])
    before = deepcopy(review.work_snapshot)
    original_time = review.submitted_at
    events_before = CustomerAuditEvent.objects.count()
    output = StringIO()
    call_command("refresh_review_physical_snapshots", actor=manager.username, stdout=output)
    review.refresh_from_db()
    assert "dry run" in output.getvalue()
    assert review.work_snapshot == before and review.submitted_at == original_time
    assert CustomerAuditEvent.objects.count() == events_before
    call_command("refresh_review_physical_snapshots", actor=manager.username, apply=True, stdout=StringIO())
    review.refresh_from_db()
    assert review.work_snapshot != before and review.submitted_at != original_time
    assert CustomerAuditEvent.objects.count() == events_before + 1
