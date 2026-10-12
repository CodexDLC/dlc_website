"""Isolation and shared-rule contracts for the German demonstration."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from features.demo import selectors, services
from features.demo.models import DemoDailyReport


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(username="demo-owner")


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(username="demo-other")


@pytest.mark.django_db
def test_seed_is_personal_idempotent_and_reset_preserves_other(owner, other):
    from features.mbg_reports.models import MbgDailyReport, MbgWorkEntry

    crm_counts = (MbgDailyReport.objects.count(), MbgWorkEntry.objects.count())
    workspace = services.ensure_workspace(owner)
    services.ensure_workspace(owner)
    second = services.ensure_workspace(other)
    assert workspace.reports.count() == 1
    assert (MbgDailyReport.objects.count(), MbgWorkEntry.objects.count()) == crm_counts
    assert workspace.employees.count() == 3
    services.reset_workspace(owner)
    assert second.reports.count() == 1
    assert workspace.reports.count() == 1


@pytest.mark.django_db
def test_report_ownership_and_forged_related_ids(owner, other):
    workspace = services.ensure_workspace(owner)
    second = services.ensure_workspace(other)
    report = workspace.reports.first()
    with pytest.raises(PermissionDenied):
        services.save_report(other, report_id=report.pk, data={}, entries=[])
    with pytest.raises(ValidationError):
        services.save_report(
            owner,
            data={"date": date.today(), "site_name": "Demo", "workforce": list(second.employees.all())},
            entries=[],
        )
    assert DemoDailyReport.objects.count() == 2


@pytest.mark.django_db
def test_hours_breaks_and_invalid_grid(owner):
    workspace = services.ensure_workspace(owner)
    people = list(workspace.employees.all())[:2]
    work = workspace.work_types.filter(is_break=False).first()
    pause = workspace.work_types.get(is_break=True)
    data = {"date": date.today(), "site_name": "Demo", "workforce": people}
    entries = [
        {"work_type": work, "participants": people, "starts_at": time(7), "ends_at": time(8), "quantity": Decimal(1)},
        {
            "work_type": pause,
            "participants": people,
            "starts_at": time(8),
            "ends_at": time(8, 30),
            "quantity": Decimal(1),
        },
    ]
    report = services.save_report(owner, data=data, entries=entries)
    prepared = selectors.report_context(owner, report.pk)
    assert prepared["totals"]["person_hours"] == Decimal(2)
    entries[0]["starts_at"] = time(7, 5)
    with pytest.raises(ValidationError):
        services.save_report(owner, data=data, entries=entries)
    assert workspace.reports.count() == 2


@pytest.mark.django_db
def test_forged_entry_ids_and_overlap_are_atomic(owner, other):
    workspace = services.ensure_workspace(owner)
    second = services.ensure_workspace(other)
    person = workspace.employees.first()
    work = workspace.work_types.filter(is_break=False).first()
    data = {"date": date.today(), "site_name": "Demo", "workforce": [person]}
    entry = {
        "work_type": work,
        "participants": [person],
        "starts_at": time(7),
        "ends_at": time(8),
        "quantity": Decimal(1),
    }
    with pytest.raises(ValidationError):
        services.save_report(owner, data=data, entries=[{**entry, "work_type": second.work_types.first()}])
    with pytest.raises(ValidationError):
        services.save_report(owner, data=data, entries=[{**entry, "participants": [second.employees.first()]}])
    with pytest.raises(ValidationError):
        services.save_report(owner, data=data, entries=[entry, {**entry, "starts_at": time(7, 30)}])
    assert workspace.reports.count() == 1


@pytest.mark.django_db
def test_edit_increments_version_and_selectors_never_seed(owner, other):
    from django.http import Http404

    with pytest.raises(Http404):
        selectors.workspace_for_actor(owner)
    workspace = services.ensure_workspace(owner)
    report = workspace.reports.first()
    context = selectors.report_context(owner, report.pk)
    services.save_report(
        owner,
        report_id=report.pk,
        data={"date": report.date, "site_name": "Changed", "workforce": list(report.workforce.all()), "version": 1},
        entries=[
            {
                "work_type": entry.work_type,
                "participants": list(entry.participants.all()),
                "starts_at": entry.starts_at,
                "ends_at": entry.ends_at,
                "quantity": entry.quantity,
            }
            for entry in context["entries"]
        ],
    )
    report.refresh_from_db()
    assert report.version == 2
    with pytest.raises(ValidationError):
        services.save_report(owner, report_id=report.pk, data={"version": 1}, entries=[])
    services.ensure_workspace(other)
    with pytest.raises(Http404):
        selectors.report_context(other, report.pk)


@pytest.mark.django_db
def test_http_auth_scope_export_and_post_reset(client, owner, other):
    from io import BytesIO

    from django.urls import reverse
    from openpyxl import load_workbook

    assert client.get(reverse("demo:work_types")).status_code == 302
    client.force_login(owner)
    workspace = services.ensure_workspace(owner)
    second = services.ensure_workspace(other)
    report = workspace.reports.first()
    for name, kwargs in (
        ("work_types", {}),
        ("reports", {}),
        ("report_new", {}),
        ("report_edit", {"pk": report.pk}),
        ("report_detail", {"pk": report.pk}),
        ("work_type_edit", {"pk": workspace.work_types.first().pk}),
    ):
        response = client.get(reverse("demo:" + name, kwargs=kwargs))
        assert response.status_code == 200
    foreign = second.reports.first()
    for name in ("report_edit", "report_detail", "report_download"):
        assert client.get(reverse("demo:" + name, kwargs={"pk": foreign.pk})).status_code == 404
    response = client.get(reverse("demo:report_download", kwargs={"pk": report.pk}))
    book = load_workbook(BytesIO(response.content))
    assert "DEMO" in book.active["A1"].value
    assert book.active["E1"].value == "DEMO - Musterfirma"
    assert "dmitri.labodin@googlemail.com" not in str([[cell.value for row in sheet for cell in row] for sheet in book])
    assert client.get(reverse("demo:reset")).status_code == 405
    assert client.post(reverse("demo:reset")).status_code == 302
    assert second.reports.count() == 1


@pytest.mark.django_db
def test_http_create_report_and_owner_scoped_form_validation(client, owner, other):
    from django.urls import reverse

    workspace = services.ensure_workspace(owner)
    second = services.ensure_workspace(other)
    person = workspace.employees.first()
    work = workspace.work_types.filter(is_break=False).first()
    client.force_login(owner)
    data = {
        "date": "2026-10-12",
        "site_name": "Fiktive Anlage",
        "address": "Demo",
        "project_number": "DEMO-2",
        "workforce": [person.pk],
        "entries-TOTAL_FORMS": 1,
        "entries-INITIAL_FORMS": 0,
        "entries-MIN_NUM_FORMS": 0,
        "entries-MAX_NUM_FORMS": 100,
        "entries-0-work_type": work.pk,
        "entries-0-participants": [person.pk],
        "entries-0-starts_at": "07:00",
        "entries-0-ends_at": "08:00",
        "entries-0-quantity": "1",
    }
    assert client.post(reverse("demo:report_new"), data).status_code == 302
    assert workspace.reports.count() == 2
    data["entries-0-work_type"] = second.work_types.first().pk
    response = client.post(reverse("demo:report_new"), data)
    assert response.status_code == 200
    assert response.context["formset"].errors
    assert workspace.reports.count() == 2
