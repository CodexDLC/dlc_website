"""Устойчивые позиции Standort и подтверждённый прирост MBG."""

from datetime import time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from features.mbg_reports.services import review_report, save_report
from features.mbg_reports.work_items import accepted_work_item_progress
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.services import save_site_work_item
from features.staff.models import Employee
from features.work_catalog.models import CableRoute, CableType, WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def work_item_data():
    manager = get_user_model().objects.create_user(username="work-item-manager", is_superuser=True)
    worker = Employee.objects.create(first_name="Work", last_name="Item", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Work items")
    site = AcObject.objects.create(group=group, name="Standort 1")
    other_site = AcObject.objects.create(group=group, name="Standort 2")
    route = CableRoute.objects.create(code="work-item-route", name_de="WR → UV-PV")
    cable = CableType.objects.create(
        code="work-item-cable", name_de="Leistungskabel", category="power", normative_hours_per_ten_meters=1
    )
    work = WorkType.objects.create(
        code="work-item-cable-laying",
        name_de="Kabelverlegung",
        direction="ac",
        unit="ten_meters",
        calculation_rule="cable",
        price_mode="per_unit",
        unit_price=Decimal("60"),
    )
    return manager, worker, site, other_site, route, cable, work


def _row(worker, work, route, cable, item, delta, *, start=time(8)):
    return {
        "participants": [worker],
        "starts_at": start,
        "ends_at": time(start.hour + 1),
        "work_type": work,
        "quantity": Decimal("1"),
        "cable_type": cable,
        "route": route,
        "standard_connections": 0,
        "heavy_connections": 0,
        "with_underconstruction": False,
        "description": item.label,
        "work_item": item,
        "completed_quantity": delta,
    }


def test_two_cables_have_distinct_ids_and_continuation_counts_once(work_item_data):
    manager, worker, site, _other, route, cable, work = work_item_data
    wr1 = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=cable
    )
    wr2 = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR2", planned_quantity=1, route=route, cable_type=cable
    )
    assert wr1.pk != wr2.pk
    assert SiteWorkItem.objects.filter(site=site).count() == 2

    submission_key = uuid4()
    first = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate() - timedelta(days=1),
        workforce=[worker],
        entries=[_row(worker, work, route, cable, wr1, Decimal("0"))],
        submit=True,
        submission_key=submission_key,
    )
    repeated = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate() - timedelta(days=1),
        workforce=[worker],
        entries=[_row(worker, work, route, cable, wr1, Decimal("0"))],
        submit=True,
        submission_key=submission_key,
    )
    assert repeated.pk == first.pk
    review_report(actor=manager, report_id=first.pk, version=first.version, decision="accept")
    second = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate(),
        workforce=[worker],
        entries=[
            _row(worker, work, route, cable, wr1, Decimal("1")),
            _row(worker, work, route, cable, wr2, Decimal("1"), start=time(9)),
        ],
        submit=True,
    )
    review_report(actor=manager, report_id=second.pk, version=second.version, decision="accept")
    legacy_row = _row(worker, work, route, cable, wr1, Decimal("1"))
    legacy_row.pop("work_item")
    legacy_row.pop("completed_quantity")
    legacy_row["description"] = "Ungeklärte alte Leitung"
    legacy = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate() - timedelta(days=2),
        workforce=[worker],
        entries=[legacy_row],
        submit=True,
    )
    review_report(actor=manager, report_id=legacy.pk, version=legacy.version, decision="accept")
    legacy_revision = legacy.revisions.first()
    legacy_snapshot = legacy_revision.snapshot
    for entry in legacy_snapshot["entries"]:
        entry.pop("work_item_id")
        entry.pop("completed_quantity")
    legacy.revisions.filter(pk=legacy_revision.pk).update(snapshot=legacy_snapshot)

    progress = accepted_work_item_progress(site_id=site.pk)
    assert {row.work_item_id: row.completed_quantity for row in progress.items} == {
        wr1.pk: Decimal("1"), wr2.pk: Decimal("1")
    }
    assert {row.work_item_id: row.actual_person_hours for row in progress.items} == {
        wr1.pk: Decimal("2"), wr2.pk: Decimal("1")
    }
    assert len(progress.unresolved_entries) == 1
    assert progress.unresolved_entries[0].description.startswith("Ungeklärte alte Leitung")
    assert progress.unresolved_entries[0].recorded_quantity == "1.00"
    assert progress.unresolved_entries[0].actual_person_hours == Decimal("1")
    assert progress.excluded_reports == ()
    assert legacy.revisions.first().snapshot == legacy_snapshot
    assert "work_item_id" not in legacy_snapshot["entries"][0]


def test_tray_continuation_has_one_physical_unit_and_two_hours(work_item_data):
    manager, worker, site, _other, _route, _cable, _work = work_item_data
    route = CableRoute.objects.create(code="work-item-nh-hv", name_de="NH → HV")
    tray = WorkType.objects.get(code="cable-tray")
    item = save_site_work_item(
        actor=manager, site=site, work_type=tray, label="NH → HV", planned_quantity=1, route=route
    )
    for days_ago, delta in ((1, Decimal("0")), (0, Decimal("1"))):
        report = save_report(
            actor=manager,
            site=site,
            work_date=timezone.localdate() - timedelta(days=days_ago),
            workforce=[worker],
            entries=[_row(worker, tray, route, None, item, delta)],
            submit=True,
        )
        review_report(actor=manager, report_id=report.pk, version=report.version, decision="accept")
    progress = accepted_work_item_progress(site_id=site.pk)
    assert len(progress.items) == 1
    assert progress.items[0].completed_quantity == Decimal("1")
    assert progress.items[0].actual_person_hours == Decimal("2")


def test_wrong_site_negative_delta_and_nonmanager_are_rejected(work_item_data):
    manager, worker, site, other_site, route, cable, work = work_item_data
    item = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=cable
    )
    outsider = get_user_model().objects.create_user(username="work-item-outsider")
    with pytest.raises(PermissionDenied):
        save_site_work_item(
            actor=outsider, site=site, work_type=work, label="WR2", planned_quantity=1, route=route, cable_type=cable
        )
    with pytest.raises(ValidationError):
        save_site_work_item(
            actor=manager, site=site, work_type=work, label="WR2", planned_quantity="not a number", route=route,
            cable_type=cable,
        )
    route.is_active = False
    route.save(update_fields=["is_active"])
    with pytest.raises(ValidationError):
        save_site_work_item(
            actor=manager, site=site, work_type=work, label="WR2", planned_quantity=1, route=route,
            cable_type=cable,
        )
    route.is_active = True
    route.save(update_fields=["is_active"])
    for target_site, delta in ((other_site, Decimal("1")), (site, Decimal("-1"))):
        with pytest.raises(ValidationError):
            save_report(
                actor=manager,
                site=target_site,
                work_date=timezone.localdate(),
                workforce=[worker],
                entries=[_row(worker, work, route, cable, item, delta)],
            )
    for broken_row in (
        {**_row(worker, work, route, cable, item, Decimal("1")), "completed_quantity": None},
        {**_row(worker, work, route, cable, item, Decimal("1")), "work_item": None},
    ):
        with pytest.raises(ValidationError):
            save_report(
                actor=manager,
                site=site,
                work_date=timezone.localdate(),
                workforce=[worker],
                entries=[broken_row],
            )


def test_current_accepted_revision_replaces_previous_delta_and_draft_is_excluded(work_item_data):
    manager, worker, site, _other, route, cable, work = work_item_data
    item = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=cable
    )
    row = _row(worker, work, route, cable, item, Decimal("1"))
    report = save_report(
        actor=manager, site=site, work_date=timezone.localdate(), workforce=[worker], entries=[row], submit=True
    )
    review_report(actor=manager, report_id=report.pk, version=report.version, decision="accept")
    report.refresh_from_db()
    assert accepted_work_item_progress(site_id=site.pk).items[0].completed_quantity == Decimal("1")

    report = save_report(
        actor=manager,
        report_id=report.pk,
        version=report.version,
        site=site,
        work_date=timezone.localdate(),
        workforce=[worker],
        entries=[{**row, "completed_quantity": Decimal("0")}],
        reason="Korrektur",
    )
    progress = accepted_work_item_progress(site_id=site.pk)
    assert progress.items[0].completed_quantity == Decimal("0")
    assert progress.items[0].actual_person_hours == Decimal("1")
    assert report.revisions.first().snapshot["entries"][0]["work_item_id"] == item.pk
    assert report.revisions.first().snapshot["entries"][0]["completed_quantity"] == "0.00"
    assert report.revisions.first().snapshot["entries"][0]["unit"] == item.unit_snapshot

    draft = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate() - timedelta(days=1),
        workforce=[worker],
        entries=[{**row, "completed_quantity": Decimal("5")}],
    )
    assert draft.status == "draft"
    assert accepted_work_item_progress(site_id=site.pk).items[0].completed_quantity == Decimal("0")

    without_links = {key: value for key, value in row.items() if key not in {"work_item", "completed_quantity"}}
    with pytest.raises(ValidationError, match="привязки"):
        save_report(
            actor=manager,
            report_id=report.pk,
            version=report.version,
            site=site,
            work_date=timezone.localdate(),
            workforce=[worker],
            entries=[without_links],
            reason="Korrektur",
        )

    report.revisions.filter(version=report.version).delete()
    incomplete = accepted_work_item_progress(site_id=site.pk)
    assert incomplete.items == ()
    assert incomplete.excluded_reports[0].report_id == report.pk
    assert incomplete.excluded_reports[0].reason == "missing_current_accepted_snapshot"


def test_hourly_work_cannot_claim_arbitrary_completed_quantity(work_item_data):
    manager, _worker, site, _other, _route, _cable, _work = work_item_data
    hourly = WorkType.objects.create(
        code="work-item-hourly", name_de="Transport", direction="ac", unit="hour",
        calculation_rule="actual", price_mode="actual_hourly",
    )
    with pytest.raises(ValidationError, match="Почасовые"):
        save_site_work_item(actor=manager, site=site, work_type=hourly, label="Transport", planned_quantity=1)


def test_heavy_cable_unit_is_frozen_from_cable_type(work_item_data):
    manager, _worker, site, _other, route, _cable, work = work_item_data
    heavy = CableType.objects.create(
        code="work-item-heavy", name_de="Schweres Kabel", category="heavy", normative_hours_per_ten_meters=1
    )
    item = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=heavy
    )
    assert item.unit_snapshot == "bis 5 m"


def test_manager_creates_work_item_from_site_and_nonmanager_cannot_edit(work_item_data, client):
    manager, _worker, site, _other, route, cable, work = work_item_data
    url = reverse("projects:work_item_new", args=[site.group_id, site.pk])
    client.force_login(manager)
    response = client.post(
        url,
        {
            "label": "WR1: Leistungskabel",
            "work_type": str(work.pk),
            "planned_quantity": "1",
            "route": str(route.pk),
            "cable_type": str(cable.pk),
        },
    )
    assert response.status_code == 302
    item = SiteWorkItem.objects.get(site=site)
    assert item.label == "WR1: Leistungskabel"
    changed = client.post(
        reverse("projects:work_item_edit", args=[site.group_id, site.pk, item.pk]),
        {
            "label": "WR1: Hauptleitung",
            "work_type": str(work.pk),
            "planned_quantity": "2",
            "route": str(route.pk),
            "cable_type": str(cable.pk),
        },
    )
    assert changed.status_code == 302
    item.refresh_from_db()
    assert item.label == "WR1: Hauptleitung"
    assert item.planned_quantity == Decimal("2")
    overview = client.get(reverse("projects:site_detail", args=[site.group_id, site.pk]))
    assert item.label in overview.content.decode()
    assert "Неразобранных принятых строк" in overview.content.decode()
    outsider = get_user_model().objects.create_user(username="work-item-viewer")
    client.force_login(outsider)
    assert client.get(url).status_code == 403


def test_http_editor_roundtrip_keeps_work_item_and_delta(work_item_data, client):
    manager, worker, site, other_site, route, cable, work = work_item_data
    item = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=cable
    )
    wrong_item = save_site_work_item(
        actor=manager, site=other_site, work_type=work, label="WR2", planned_quantity=1, route=route,
        cable_type=cable,
    )
    client.force_login(manager)
    new_url = f"{reverse('mbg_reports:new')}?group={site.group_id}&site={site.pk}"
    initial = client.get(new_url)
    assert item in initial.context["formset"].forms[0].fields["work_item"].queryset
    assert wrong_item not in initial.context["formset"].forms[0].fields["work_item"].queryset
    choices = client.get(reverse("mbg_reports:work_item_options"), {"site": site.pk}).json()["items"]
    assert [choice["id"] for choice in choices] == [item.pk]

    payload = {
        "action": "save",
        "group": str(site.group_id),
        "site": str(site.pk),
        "work_date": str(timezone.localdate()),
        "workforce": [str(worker.pk)],
        "submission_key": str(uuid4()),
        "entries-TOTAL_FORMS": "1",
        "entries-INITIAL_FORMS": "0",
        "entries-MIN_NUM_FORMS": "1",
        "entries-MAX_NUM_FORMS": "100",
        "entries-0-participants": [str(worker.pk)],
        "entries-0-starts_at": "08:00",
        "entries-0-ends_at": "09:00",
        "entries-0-work_type": str(work.pk),
        "entries-0-quantity": "1",
        "entries-0-cable_type": str(cable.pk),
        "entries-0-route": str(route.pk),
        "entries-0-standard_connections": "0",
        "entries-0-heavy_connections": "0",
        "entries-0-description": "WR1",
        "entries-0-work_item": str(item.pk),
        "entries-0-completed_quantity": "0",
    }
    created = client.post(reverse("mbg_reports:new"), payload)
    assert created.status_code == 302
    from features.mbg_reports.models import MbgDailyReport

    report = MbgDailyReport.objects.get(site=site)
    assert report.entries.get().work_item_id == item.pk
    assert report.entries.get().completed_quantity == Decimal("0")
    detail = client.get(reverse("mbg_reports:detail", args=[report.pk]))
    assert "Прирост выполненного объёма" in detail.content.decode()
    assert 'data-completed-quantity="0.00"' in detail.content.decode()
    overview = client.get(reverse("projects:site_detail", args=[site.group_id, site.pk]))
    assert overview.context["work_plan"].rows[0].completed_quantity == Decimal("0")
    assert overview.context["work_plan"].rows[0].actual_person_hours == Decimal("0")

    add_payload = {**payload, "action": "add"}
    added = client.post(reverse("mbg_reports:edit", args=[report.pk]), add_payload)
    assert added.status_code == 200
    assert added.context["formset"].forms[0].initial["work_item"] == str(item.pk)
    assert added.context["formset"].forms[0].initial["completed_quantity"] == "0"

    edit_url = reverse("mbg_reports:edit", args=[report.pk])
    edit = client.get(edit_url)
    assert edit.context["formset"].forms[0].initial["work_item"] == item.pk
    assert edit.context["formset"].forms[0].initial["completed_quantity"] == Decimal("0")
    payload["version"] = str(report.version)
    payload["submission_key"] = str(report.submission_key)
    payload["entries-INITIAL_FORMS"] = "1"
    payload["entries-0-completed_quantity"] = "1"
    assert client.post(edit_url, payload).status_code == 302
    assert report.entries.get().work_item_id == item.pk
    assert report.entries.get().completed_quantity == Decimal("1")

    payload["version"] = str(report.version + 1)
    payload["entries-0-work_item"] = str(wrong_item.pk)
    invalid = client.post(edit_url, payload)
    assert invalid.status_code == 200
    assert "work_item" in invalid.context["formset"].forms[0].errors
    assert report.entries.get().work_item_id == item.pk


def test_used_work_item_identity_cannot_change_even_when_only_old_snapshot_references_it(work_item_data):
    manager, worker, site, _other, route, cable, work = work_item_data
    item = save_site_work_item(
        actor=manager, site=site, work_type=work, label="WR1", planned_quantity=1, route=route, cable_type=cable
    )
    report = save_report(
        actor=manager,
        site=site,
        work_date=timezone.localdate(),
        workforce=[worker],
        entries=[_row(worker, work, route, cable, item, Decimal("1"))],
    )
    other_route = CableRoute.objects.create(code="work-item-other-route", name_de="WR → HV")
    with pytest.raises(ValidationError, match="использованной"):
        save_site_work_item(
            actor=manager,
            site=site,
            work_type=work,
            label="WR1",
            planned_quantity=1,
            route=other_route,
            cable_type=cable,
            work_item_id=item.pk,
        )
    report.entries.all().delete()
    with pytest.raises(ValidationError, match="использованной"):
        save_site_work_item(
            actor=manager,
            site=site,
            work_type=work,
            label="WR1",
            planned_quantity=1,
            route=other_route,
            cable_type=cable,
            work_item_id=item.pk,
        )
