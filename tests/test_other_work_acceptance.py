from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


def test_other_work_flag_snapshot_and_edit(client):
    actor = get_user_model().objects.create_superuser(username="extra-owner")
    worker = Employee.objects.create(first_name="A", last_name="B", has_ac_access=True)
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Extra"), name="Site")
    work = WorkType.objects.get(code="sonstige")
    base = {"participants": [worker], "work_type": work, "quantity": Decimal("1")}
    entries = [
        dict(base, starts_at=time(8), ends_at=time(9), include_in_acceptance=False, internal_only=True),
        dict(base, starts_at=time(9), ends_at=time(10), include_in_acceptance=True, internal_only=False),
    ]
    report = save_report(
        actor=actor, site=site, work_date=date(2026, 10, 2), workforce=[worker], entries=entries, submit=True
    )
    report = review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
    snapshot = report.revisions.get(version=report.version).snapshot
    assert [e["include_in_acceptance"] for e in snapshot["entries"]] == [False, True]
    assert load_accepted_reports_dataset(site_ids=[site.pk]).all_sites[site.pk].day_facts[0].total_hours == Decimal("2")
    client.force_login(actor)
    response = client.get(reverse("mbg_reports:edit", args=[report.pk]))
    assert response.context["formset"].forms[1]["include_in_acceptance"].value() is True
    assert 'data-work-code="sonstige"' in response.content.decode()
    frozen = snapshot["entries"][1]["include_in_acceptance"]
    updated = save_report(
        actor=actor,
        site=site,
        work_date=report.work_date,
        workforce=[worker],
        entries=entries,
        report_id=report.pk,
        version=report.version,
        reason="edit",
    )
    assert updated.entries.order_by("starts_at")[1].include_in_acceptance is True
    assert report.revisions.get(version=report.version).snapshot["entries"][1]["include_in_acceptance"] == frozen
    entries[1]["work_type"] = WorkType.objects.get(code="uv-montage")
    with pytest.raises(ValidationError):
        save_report(
            actor=actor,
            site=site,
            work_date=report.work_date,
            workforce=[worker],
            entries=entries,
            report_id=updated.pk,
            version=updated.version,
            reason="correct",
        )


def test_form_sets_internal_flag_and_validates_work_type():
    from features.mbg_reports.forms import EntryForm

    worker = Employee.objects.create(first_name="Form", last_name="Worker", has_ac_access=True)
    other = WorkType.objects.get(code="sonstige")
    data = {
        "participants": [worker.pk],
        "starts_at": "08:00",
        "ends_at": "09:00",
        "work_type": other.pk,
        "quantity": "1",
        "standard_connections": "0",
        "heavy_connections": "0",
    }
    form = EntryForm(data=data)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["internal_only"] and not form.cleaned_data["include_in_acceptance"]
    form = EntryForm(data={**data, "include_in_acceptance": "on", "internal_only": "on"})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["include_in_acceptance"] and not form.cleaned_data["internal_only"]
    form = EntryForm(
        data={**data, "include_in_acceptance": "on", "work_type": WorkType.objects.get(code="uv-montage").pk}
    )
    assert not form.is_valid() and "include_in_acceptance" in form.errors


def test_other_work_unchecked_and_legacy_are_private_and_not_billed():
    from features.customer_portal.selectors import accepted_daily_work
    from features.mbg_reports.customer_billing_selectors import customer_billing_summary

    actor = get_user_model().objects.create_superuser(username="unchecked-owner")
    worker = Employee.objects.create(first_name="No", last_name="Invoice", has_ac_access=True)
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="No invoice"), name="Site")
    entry = {
        "participants": [worker],
        "work_type": WorkType.objects.get(code="sonstige"),
        "quantity": Decimal("1"),
        "starts_at": time(8),
        "ends_at": time(9),
        "description": "Private task",
    }
    report = save_report(
        actor=actor, site=site, work_date=date(2026, 10, 4), workforce=[worker], entries=[entry], submit=True
    )
    report = review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
    assert report.entries.get().internal_only is True
    assert not accepted_daily_work(site)
    assert load_accepted_reports_dataset(site_ids=[site.pk]).all_sites[site.pk].day_facts[0].total_hours == Decimal("1")
    summary = customer_billing_summary(site)
    assert next(row for row in summary.rows if row.code == "01.0090").quantity == 0
    assert summary.amount == 0
    revision = report.revisions.get(version=report.version)
    snapshot = revision.snapshot
    snapshot["entries"][0].pop("include_in_acceptance")
    snapshot["entries"][0]["internal_only"] = False
    revision.snapshot = snapshot
    revision.save(update_fields=["snapshot"])
    summary = customer_billing_summary(site)
    assert next(row for row in summary.rows if row.code == "01.0090").amount == 0
    assert summary.amount == 0


def test_mixed_legacy_and_confirmed_same_description_only_counts_confirmed():
    from features.mbg_reports.customer_billing_selectors import customer_billing_summary

    actor = get_user_model().objects.create_superuser(username="mixed-extra-owner")
    worker = Employee.objects.create(first_name="Mixed", last_name="Worker", has_ac_access=True)
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Mixed extra"), name="Site")
    base = {
        "participants": [worker],
        "work_type": WorkType.objects.get(code="sonstige"),
        "quantity": Decimal("1"),
        "description": "Same description",
        "starts_at": time(8),
        "ends_at": time(9),
        "include_in_acceptance": True,
    }
    for day in (5, 6):
        report = save_report(
            actor=actor, site=site, work_date=date(2026, 10, day), workforce=[worker], entries=[base], submit=True
        )
        report = review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
        if day == 5:
            revision = report.revisions.get(version=report.version)
            snapshot = revision.snapshot
            snapshot["entries"][0].pop("include_in_acceptance")
            revision.snapshot = snapshot
            revision.save(update_fields=["snapshot"])
    summary = customer_billing_summary(site)
    row = next(row for row in summary.rows if row.code == "01.0090")
    assert row.quantity == Decimal("1") and row.amount == Decimal("40")
    assert summary.amount == Decimal("40")
