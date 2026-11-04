from copy import deepcopy
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from features.customer_portal.models import CustomerAuditEvent, SiteReview
from features.customer_portal.selectors import customer_site_detail
from features.customer_portal.services import decide_review, grant_membership, submit_for_review
from features.projects.models import AcObject, Client, ProjectGroup
from features.work_catalog.models import CustomerWorkPosition

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    users = get_user_model()
    manager = users.objects.create_superuser(username="catalog-review-manager")
    customer = users.objects.create_user(username="catalog-review-customer")
    company = Client.objects.create(name="MBG")
    grant_membership(actor=manager, user=customer, client=company)
    site = AcObject.objects.create(
        group=ProjectGroup.objects.create(name="Review", client=company), name="Haus", status="completed"
    )
    return manager, customer, site


def test_full_catalog_decisions_and_prices(ctx):
    manager, customer, site = ctx
    review = submit_for_review(actor=manager, site=site)
    assert len(review.work_snapshot) == 21
    assert all(row["quantity"] == "0.00" and row["key"].startswith("customer:") for row in review.work_snapshot)
    assert not any("price" in str(row) or "hours" in str(row) for row in review.work_snapshot)
    position = CustomerWorkPosition.objects.get(code="10.010")
    position.unit_price = Decimal("999")
    position.save()
    assert not customer_site_detail(site).review_stale
    decisions = {row["key"]: {"decision": "accepted", "comment": ""} for row in review.work_snapshot}
    result = decide_review(
        actor=customer,
        site=site,
        decisions=decisions,
        snapshot_digest=review.snapshot_digest,
        submission_token=review.submitted_at.isoformat(),
    )
    assert result.status == "accepted"


def test_incomplete_site_cannot_submit_or_decide_and_queue_excludes(ctx, client):
    manager, customer, site = ctx
    review = submit_for_review(actor=manager, site=site)
    site.status = "started"
    site.save()
    with pytest.raises(ValidationError):
        submit_for_review(actor=manager, site=site)
    with pytest.raises(ValidationError):
        decide_review(
            actor=customer,
            site=site,
            decisions={},
            snapshot_digest=review.snapshot_digest,
            submission_token=review.submitted_at.isoformat(),
        )
    client.force_login(customer)
    assert review not in client.get(reverse("customer_portal:reviews")).context["reviews"]


def test_legacy_pending_blocked_and_resubmit_audited(ctx):
    manager, customer, site = ctx
    review = SiteReview.objects.create(
        site=site,
        status="submitted",
        snapshot_digest="old",
        work_snapshot=[{"key": "1", "name": "old work", "unit": "piece"}],
        item_decisions={"1": {"decision": "accepted"}},
    )
    old = deepcopy(review.work_snapshot)
    assert customer_site_detail(site).review_stale
    with pytest.raises(ValidationError):
        decide_review(actor=customer, site=site, decisions={}, snapshot_digest="old", submission_token="")
    review = submit_for_review(actor=manager, site=site)
    assert len(review.work_snapshot) == 21 and review.item_decisions == {}
    assert CustomerAuditEvent.objects.filter(action="review_submitted").latest("pk").before["work_snapshot"] == old


def test_page_includes_bulk_control_and_catalog_codes(ctx, client, monkeypatch):
    manager, customer, site = ctx
    submit_for_review(actor=manager, site=site)
    monkeypatch.setattr(
        "features.integrations.nextcloud.services.get_site_photo_summary",
        lambda site, **kw: {"status": "ok", "count": 0},
    )
    client.force_login(customer)
    response = client.get(reverse("customer_portal:site", args=[site.pk]))
    assert response.status_code == 200
    assert "data-review-accept-all" in response.content.decode() and "10.010" in response.content.decode()


def test_unmapped_patch_is_zero_and_not_exposed_in_review(ctx, client, monkeypatch):
    from datetime import date

    from features.mbg_reports.models import MbgDailyReport, MbgReportRevision

    manager, customer, site = ctx
    report = MbgDailyReport.objects.create(site=site, author=manager, work_date=date(2026, 10, 1), status="accepted")
    MbgReportRevision.objects.create(
        report=report,
        actor=manager,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "entries": [
                {
                    "work_type_code": "patch-cable",
                    "description": "Private patch details",
                    "unit": "piece",
                    "quantity": "1",
                    "completed_quantity": "1",
                    "actual_person_hours": "2",
                }
            ],
        },
    )
    review = submit_for_review(actor=manager, site=site)
    assert next(row for row in review.work_snapshot if row["code"] == "01.0200")["quantity"] == "0.00"
    assert "Private patch details" not in str(review.work_snapshot)
    monkeypatch.setattr(
        "features.integrations.nextcloud.services.get_site_photo_summary",
        lambda site, **kw: {"status": "ok", "count": 0},
    )
    client.force_login(customer)
    html = client.get(reverse("customer_portal:site", args=[site.pk])).content.decode()
    review_section = html.split('id="customer-review"', 1)[1].split("</section>", 1)[0]
    assert "Private patch details" not in review_section
