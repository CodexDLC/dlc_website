"""Права и жизненный цикл первого кабинета заказчика."""

from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as HttpClient
from django.urls import reverse
from features.customer_portal.models import ClientMembership, CustomerAuditEvent, PlanProposal, SiteReview
from features.customer_portal.selectors import accepted_daily_work
from features.customer_portal.services import (
    decide_review,
    grant_membership,
    propose_manual_item,
    propose_plan,
    review_plan,
    save_customer_group,
    save_customer_site,
    submit_for_review,
)
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, Client, ProjectGroup, SiteWorkItem
from features.projects.services import save_group, save_object, save_site_work_item, set_site_status
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    users = get_user_model()
    manager = users.objects.create_superuser(username="portal-admin", email="admin@example.test", password=None)
    alice = users.objects.create_user(username="portal-a")
    bob = users.objects.create_user(username="portal-b")
    a = Client.objects.create(name="Auftraggeber A")
    b = Client.objects.create(name="Auftraggeber B")
    grant_membership(actor=manager, user=alice, client=a, can_manage_projects=True)
    grant_membership(actor=manager, user=bob, client=b, can_manage_projects=False)
    group_a = ProjectGroup.objects.create(name="Anlage A", client=a)
    group_b = ProjectGroup.objects.create(name="Anlage B", client=b)
    site_a = AcObject.objects.create(group=group_a, name="Haus A")
    site_b = AcObject.objects.create(group=group_b, name="Haus B")
    return manager, alice, bob, a, b, group_a, group_b, site_a, site_b


def test_customer_routes_are_isolated_and_internal_routes_denied(actors, client):
    _manager, alice, _bob, _a, _b, group_a, group_b, site_a, site_b = actors
    client.force_login(alice)
    assert client.get(reverse("customer_portal:home")).status_code == 200
    assert client.get(reverse("customer_portal:group", args=[group_a.pk])).status_code == 200
    assert client.get(reverse("customer_portal:group", args=[group_b.pk])).status_code == 404
    assert client.get(reverse("customer_portal:site", args=[site_a.pk])).status_code == 200
    assert client.get(reverse("customer_portal:site", args=[site_b.pk])).status_code == 404
    assert client.get(reverse("projects:site_detail", args=[group_a.pk, site_a.pk])).status_code == 403
    assert client.get(reverse("project_media:list", args=[group_a.pk])).status_code == 403
    for name in ("objects", "works", "reviews", "documents", "audit"):
        assert client.get(reverse(f"customer_portal:{name}")).status_code == 200
    page = client.get(reverse("customer_portal:home")).content.decode()
    assert "Кабинет заказчика" in page
    assert "Администрирование" not in page
    assert group_b.name not in page


def test_capability_controls_creation_and_assignment_never_comes_from_post(actors, client):
    _manager, alice, bob, a, b, *_ = actors
    created = save_customer_group(actor=alice, data={"name": "Neue Anlage", "address": "Berlin", "has_ac": True})
    assert created.client_id == a.pk
    assert CustomerAuditEvent.objects.filter(action="group_created", target_id=created.pk).exists()
    with pytest.raises(PermissionDenied):
        save_customer_group(actor=bob, data={"name": "Verboten", "client": a, "has_ac": True})
    with pytest.raises(PermissionDenied):
        grant_membership(actor=alice, user=bob, client=a, can_manage_projects=True)
    client.force_login(alice)
    response = client.post(
        reverse("customer_portal:group_new"),
        {
            "name": "POST Anlage",
            "address": "Berlin",
            "client": b.pk,
            "has_ac": "on",
        },
    )
    assert response.status_code == 302
    assert ProjectGroup.objects.get(name="POST Anlage").client_id == a.pk


def test_proposal_requires_admin_approval_and_does_not_touch_accepted_history(actors):
    manager, alice, *_rest, site_a, _site_b = actors
    report = MbgDailyReport.objects.create(
        author=manager,
        site=site_a,
        work_date=date(2026, 10, 3),
        status="accepted",
        version=1,
        submission_key=uuid4(),
    )
    revision = MbgReportRevision.objects.create(
        report=report,
        actor=manager,
        version=1,
        action="accept",
        snapshot={"status": "accepted", "entries": []},
    )
    proposal = propose_plan(actor=alice, site=site_a, selected={"uv-mount": "1"})
    assert PlanProposal.objects.filter(pk=proposal.pk, status="pending").exists()
    assert SiteWorkItem.objects.filter(site=site_a).count() == 0
    review_plan(actor=manager, proposal=proposal, approve=True, reason="Geprüft")
    assert SiteWorkItem.objects.filter(site=site_a).count() == 1
    report.refresh_from_db()
    revision.refresh_from_db()
    assert (report.version, report.status, revision.snapshot) == (1, "accepted", {"status": "accepted", "entries": []})
    with pytest.raises(ValidationError):
        review_plan(actor=manager, proposal=proposal, approve=True, reason="Wiederholen")
    assert SiteWorkItem.objects.filter(site=site_a).count() == 1


def test_review_requires_fresh_accepted_snapshot_and_return_reason(actors):
    manager, alice, *_rest, site_a, _site_b = actors
    report = MbgDailyReport.objects.create(
        author=manager,
        site=site_a,
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
        snapshot={"status": "accepted", "entries": []},
    )
    review = submit_for_review(actor=manager, site=site_a)
    assert review.status == "submitted"
    with pytest.raises(ValidationError):
        decide_review(actor=alice, site=site_a, accept=False, reason="")
    report.version = 2
    report.save(update_fields=["version"])
    with pytest.raises(ValidationError):
        decide_review(actor=alice, site=site_a, accept=True)
    assert SiteReview.objects.get(site=site_a).status == "submitted"


def test_customer_pdf_requires_signature_and_cross_client_download_is_denied(actors, client, settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path
    _manager, alice, bob, _a, _b, group_a, _group_b, *_ = actors
    client.force_login(alice)
    bad = SimpleUploadedFile("plan.pdf", b"not-pdf", content_type="application/pdf")
    response = client.post(reverse("customer_portal:file_upload", args=[group_a.pk]), {"file": bad})
    assert response.status_code == 200
    assert b"PDF" in response.content
    good = SimpleUploadedFile("plan.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")
    response = client.post(reverse("customer_portal:file_upload", args=[group_a.pk]), {"file": good})
    assert response.status_code == 302
    from features.project_media.models import ProjectFile

    attachment = ProjectFile.objects.get(group=group_a)
    assert attachment.customer_visible
    client.force_login(bob)
    assert client.get(reverse("customer_portal:file_download", args=[attachment.pk])).status_code == 404


def test_cross_client_posts_and_readonly_capability_are_denied(actors, client):
    _manager, alice, bob, _a, _b, _group_a, group_b, _site_a, site_b = actors
    client.force_login(alice)
    assert (
        client.post(reverse("customer_portal:group_edit", args=[group_b.pk]), {"name": "Intrusion"}).status_code == 404
    )
    assert client.post(reverse("customer_portal:site_new", args=[group_b.pk]), {"name": "Intrusion"}).status_code == 404
    assert (
        client.post(reverse("customer_portal:plan_proposal", args=[site_b.pk]), {"step": "submit"}).status_code == 404
    )
    assert (
        client.post(reverse("customer_portal:review_decision", args=[site_b.pk]), {"decision": "accept"}).status_code
        == 404
    )
    assert client.get(reverse("customer_portal:group_work_xlsx", args=[group_b.pk])).status_code == 404
    client.force_login(bob)
    assert client.get(reverse("customer_portal:group_new")).status_code == 403
    assert client.get(reverse("customer_portal:plan_proposal", args=[site_b.pk])).status_code == 403
    assert client.get(reverse("customer_portal:file_upload", args=[group_b.pk])).status_code == 403
    ClientMembership.objects.filter(user=bob).update(is_active=False)
    assert client.get(reverse("projects:site_detail", args=[group_b.pk, site_b.pk])).status_code == 403
    assert client.get(reverse("customer_portal:home")).status_code == 403


def test_customer_post_requires_csrf(actors):
    _manager, alice, *_ = actors
    csrf_client = HttpClient(enforce_csrf_checks=True)
    csrf_client.force_login(alice)
    assert csrf_client.post(reverse("customer_portal:group_new"), {"name": "No token"}).status_code == 403


def test_review_accept_return_resubmit_and_audit_are_separate_from_site_status(actors):
    manager, alice, *_rest, site_a, _site_b = actors
    report = MbgDailyReport.objects.create(
        author=manager,
        site=site_a,
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
        snapshot={"status": "accepted", "entries": []},
    )
    submit_for_review(actor=manager, site=site_a)
    decision = decide_review(actor=alice, site=site_a, accept=False, reason="Kabel fehlt")
    assert (decision.status, decision.remark, site_a.status) == ("returned", "Kabel fehlt", "not_started")
    submit_for_review(actor=manager, site=site_a)
    decision = decide_review(actor=alice, site=site_a, accept=True)
    assert decision.status == "accepted" and decision.remark == ""
    assert CustomerAuditEvent.objects.filter(client=site_a.group.client, action="review_decided").count() == 2


def test_started_metadata_update_requires_reason_and_audit_has_before_after(actors):
    _manager, alice, *_rest, group_a, _group_b, site_a, _site_b = actors
    site_a.status = "started"
    site_a.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        save_customer_site(actor=alice, group=group_a, site_id=site_a.pk, data={"address": "Neue Str. 3"})
    saved = save_customer_site(
        actor=alice, group=group_a, site_id=site_a.pk, data={"address": "Neue Str. 3"}, reason="Adresse korrigiert"
    )
    event = CustomerAuditEvent.objects.get(action="site_updated", target_id=saved.pk)
    assert event.before["address"] == "" and event.after["address"] == "Neue Str. 3"
    assert event.reason == "Adresse korrigiert"
    with pytest.raises(ValueError):
        event.save()


def test_customer_excel_uses_accepted_snapshot_without_prices_or_formulas(actors, client):
    from io import BytesIO

    from openpyxl import load_workbook

    manager, alice, *_rest, site_a, _site_b = actors
    report = MbgDailyReport.objects.create(
        author=manager,
        site=site_a,
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
                    "description": '=HYPERLINK("evil")',
                    "unit": "Stk.",
                    "quantity": "1",
                    "completed_quantity": "0",
                    "actual_person_hours": "1",
                    "unit_price": "SECRET_PRICE",
                }
            ],
        },
    )
    assert accepted_daily_work(site_a)[0].quantity == "0"
    client.force_login(alice)
    response = client.get(reverse("customer_portal:accepted_work_xlsx", args=[site_a.pk]))
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook.active
    cells = [cell for row in sheet for cell in row]
    assert any(cell.value == '=HYPERLINK("evil")' and cell.data_type == "s" for cell in cells)
    assert not any("SECRET_PRICE" in str(cell.value) for cell in cells)


def test_existing_pdf_is_hidden_until_admin_explicitly_exposes_it(actors, client, settings, tmp_path):
    from features.project_media.models import ProjectFile

    settings.PRIVATE_MEDIA_ROOT = tmp_path
    manager, alice, _bob, _a, _b, group_a, *_ = actors
    hidden = ProjectFile.objects.create(
        group=group_a,
        kind="document",
        file=SimpleUploadedFile("existing.pdf", b"%PDF-1.4\n%%EOF"),
        original_name="existing.pdf",
        content_type="application/pdf",
        size=14,
        uploaded_by=manager,
    )
    client.force_login(alice)
    assert client.get(reverse("customer_portal:file_download", args=[hidden.pk])).status_code == 404
    assert "existing.pdf" not in client.get(reverse("customer_portal:documents")).content.decode()
    client.force_login(manager)
    response = client.post(
        reverse("customer_portal:file_visibility", args=[hidden.pk]),
        {
            "visible": "1",
            "reason": "Freigabe geprüft",
        },
    )
    assert response.status_code == 302
    client.force_login(alice)
    assert client.get(reverse("customer_portal:file_download", args=[hidden.pk])).status_code == 200
    assert CustomerAuditEvent.objects.filter(action="document_visibility", reason="Freigabe geprüft").exists()


def test_manual_catalog_position_is_proposed_then_admin_creates_it_once(actors):
    manager, alice, *_rest, site_a, _site_b = actors
    work_type = WorkType.objects.get(code="uv-montage")
    proposal = propose_manual_item(
        actor=alice, site=site_a, work_type=work_type, label="Zusatz UV-PV",
        planned_quantity="2", with_underconstruction=False,
    )
    assert SiteWorkItem.objects.filter(site=site_a).count() == 0
    review_plan(actor=manager, proposal=proposal, approve=True, reason="Zusatz geprüft")
    assert SiteWorkItem.objects.get(site=site_a, label="Zusatz UV-PV").planned_quantity == 2
    with pytest.raises(ValidationError):
        review_plan(actor=manager, proposal=proposal, approve=True, reason="Doppelt")
    with pytest.raises(ValidationError):
        propose_manual_item(
            actor=alice, site=site_a, work_type=work_type, label="Ungültig", planned_quantity="0",
        )
    hourly = WorkType.objects.filter(unit="hour").first()
    if hourly:
        with pytest.raises(ValidationError):
            propose_manual_item(actor=alice, site=site_a, work_type=hourly, label="Stunden", planned_quantity="1")


def test_internal_project_services_emit_same_customer_audit(actors):
    manager, _alice, *_rest, group_a, _group_b, site_a, _site_b = actors
    save_group(actor=manager, group_id=group_a.pk, data={"name": "Anlage A neu"})
    save_object(actor=manager, group=group_a, object_id=site_a.pk, data={"address": "Berlin"})
    work_type = WorkType.objects.get(code="uv-montage")
    item = save_site_work_item(actor=manager, site=site_a, work_type=work_type,
                               label="Montage UV-PV", planned_quantity="1")
    set_site_status(actor=manager, site=site_a, status="started")
    actions = set(CustomerAuditEvent.objects.filter(client=group_a.client).values_list("action", flat=True))
    assert {"group_updated", "site_updated", "work_item_created", "site_status_changed"} <= actions
    group_event = CustomerAuditEvent.objects.get(action="group_updated", target_id=group_a.pk)
    assert group_event.before["name"] == "Anlage A"
    assert group_event.after["name"] == "Anlage A neu"
    assert CustomerAuditEvent.objects.filter(action="work_item_created", target_id=item.pk).exists()


def test_manual_item_form_requires_capability_and_ignores_foreign_site(actors, client):
    _manager, alice, bob, _a, _b, _group_a, _group_b, site_a, site_b = actors
    work_type = WorkType.objects.get(code="uv-montage")
    payload = {"work_type": work_type.pk, "label": "Zusatz Formular", "planned_quantity": "3"}
    client.force_login(bob)
    assert client.post(reverse("customer_portal:manual_item_proposal", args=[site_b.pk]), payload).status_code == 403
    client.force_login(alice)
    assert client.post(reverse("customer_portal:manual_item_proposal", args=[site_b.pk]), payload).status_code == 404
    assert client.post(reverse("customer_portal:manual_item_proposal", args=[site_a.pk]), payload).status_code == 302
    assert PlanProposal.objects.filter(site=site_a, status="pending").count() == 1
    assert SiteWorkItem.objects.filter(site=site_a).count() == 0


def test_group_without_client_is_not_audited(actors):
    manager, *_rest = actors
    group = save_group(actor=manager, data={"name": "Ohne Auftraggeber"})
    save_group(actor=manager, group_id=group.pk, data={"name": "Ohne Auftraggeber 2"})
    assert not CustomerAuditEvent.objects.filter(target_id=group.pk, target_type="ProjectGroup").exists()
