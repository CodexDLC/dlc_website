"""Ценовые срезы MBG не подменяют неизвестную цену или Menge нулём."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from features.mbg_reports.exports import generate_performance_report
from features.mbg_reports.models import PerformanceExport
from features.mbg_reports.selectors import group_position_summary, site_position_summary
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.projects.read_models import site_activity_map
from features.projects.services import save_site_work_item
from features.staff.models import Employee
from features.work_catalog.models import CableRoute, CableType, WorkType
from openpyxl import load_workbook

pytestmark = pytest.mark.django_db


@pytest.fixture
def priced_data():
    admin = get_user_model().objects.create_user(username="priced-owner", is_superuser=True)
    worker = Employee.objects.create(first_name="Ada", last_name="Montage", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Anlage Preis")
    site = AcObject.objects.create(
        group=group, name="Haus 1", address="Straße 1", project_number="P-1", status="started"
    )
    return admin, worker, group, site


def _entry(worker, work, *, description="", route=None, cable_type=None, start=time(8), end=time(9),
           quantity=1, item=None, delta=None, with_underconstruction=False, standard_connections=0):
    return {
        "participants": [worker], "starts_at": start, "ends_at": end, "work_type": work,
        "description": description, "route": route, "cable_type": cable_type,
        "quantity": Decimal(str(quantity)), "work_item": item, "completed_quantity": delta,
        "with_underconstruction": with_underconstruction,
        "standard_connections": standard_connections, "heavy_connections": 0,
    }


def _accepted(admin, worker, site, day, entries):
    report = save_report(
        actor=admin, site=site, work_date=day, workforce=[worker], entries=entries, submit=True
    )
    return review_report(actor=admin, report_id=report.pk, version=report.version, decision="accept")


def test_priced_summary_keeps_distinct_wr_and_continued_tray_and_unknown_legacy(priced_data):
    admin, worker, group, site = priced_data
    cable_work = WorkType.objects.get(code="cable-laying")
    tray_work = WorkType.objects.get(code="cable-tray")
    cable = CableType.objects.get(code="power-5x10")
    route = CableRoute.objects.create(code="priced-nh-hv", name_de="NH → HV")
    cable1 = save_site_work_item(
        actor=admin, site=site, work_type=cable_work, label="WR1", planned_quantity=1,
        route=route, cable_type=cable,
    )
    cable2 = save_site_work_item(
        actor=admin, site=site, work_type=cable_work, label="WR2", planned_quantity=1,
        route=route, cable_type=cable,
    )
    tray = save_site_work_item(
        actor=admin, site=site, work_type=tray_work, label="NH-HV", planned_quantity=1, route=route,
        with_underconstruction=True,
    )
    _accepted(admin, worker, site, date(2026, 9, 21), [
        _entry(worker, cable_work, description="WR1", route=route, cable_type=cable,
               item=cable1, delta=Decimal("1")),
        _entry(worker, cable_work, description="WR2", route=route, cable_type=cable,
               item=cable2, delta=Decimal("1"), start=time(9), end=time(10)),
        _entry(worker, tray_work, description="NH-HV", route=route, item=tray,
               delta=Decimal("0"), start=time(10), end=time(11), with_underconstruction=True),
    ])
    _accepted(admin, worker, site, date(2026, 9, 22), [
        _entry(worker, tray_work, description="NH-HV", route=route, item=tray,
               delta=Decimal("1"), with_underconstruction=True),
        _entry(worker, tray_work, description="Alte Trasse", route=route,
               quantity=3, start=time(9), end=time(10)),
    ])

    rows = site_position_summary(site)
    by_item = {row.work_item_id: row for row in rows if row.work_item_id is not None}
    assert {cable1.pk, cable2.pk, tray.pk} <= by_item.keys()
    assert by_item[cable1.pk].quantity == by_item[cable2.pk].quantity == Decimal("1")
    assert by_item[tray.pk].quantity == Decimal("1")
    assert by_item[tray.pk].actual_person_hours == Decimal("2")
    assert by_item[tray.pk].sources[0]["with_underconstruction"] is True
    assert all(by_item[item.pk].amount == Decimal("0.00") and by_item[item.pk].unit_price == Decimal("0.00")
               for item in (cable1, cable2, tray))
    legacy = next(row for row in rows if row.name.startswith("Alte Trasse"))
    assert legacy.quantity is None and legacy.amount is None
    assert legacy.sources[0]["recorded_quantity"] == "3.00"
    assert {row.work_item_id for row in group_position_summary(group) if row.work_item_id} == {
        cable1.pk, cable2.pk, tray.pk
    }


def test_priced_summary_hourly_agreement_free_and_drafts_are_distinct(priced_data):
    admin, worker, _group, site = priced_data
    material = WorkType.objects.get(code="material")
    photo = WorkType.objects.get(code="photo-documentation")
    tray = WorkType.objects.get(code="cable-tray")
    route = CableRoute.objects.create(code="priced-legacy", name_de="Alte Trasse")
    _accepted(admin, worker, site, date(2026, 9, 21), [
        _entry(worker, material, description="Lieferung", quantity=2, end=time(10, 30)),
        _entry(worker, photo, description="Fotodokumentation", start=time(11), end=time(12)),
        _entry(worker, tray, description="Trasse", route=route, start=time(12), end=time(13)),
    ])
    _accepted(admin, worker, site, date(2026, 9, 22), [
        _entry(worker, material, description="Lieferung", quantity=9, end=time(12)),
    ])
    save_report(
        actor=admin, site=site, work_date=date(2026, 9, 23), workforce=[worker],
        entries=[_entry(worker, material, description="Entwurf", end=time(10))],
    )

    rows = site_position_summary(site)
    delivery = next(row for row in rows if row.name == "Lieferung")
    free = next(row for row in rows if row.name == "Fotodokumentation")
    unknown = next(row for row in rows if row.name.startswith("Trasse"))
    assert delivery.quantity == Decimal("6.5") and delivery.unit == "Std."
    assert delivery.price_state == "agreed_hourly"
    assert delivery.unit_price == Decimal("0.00") and delivery.amount == Decimal("0.00")
    assert free.price_state == "free" and free.amount == Decimal("0")
    assert free.actual_person_hours == Decimal("1")
    assert unknown.price_state == "unagreed" and unknown.amount is None and unknown.quantity is None
    assert not any(row.name == "Entwurf" for row in rows)
    activity = site_activity_map([site.pk])[site.pk]
    assert activity.known_subtotal == Decimal("0.00")
    assert activity.accepted_amount is None


def test_priced_excel_marks_incomplete_totals_and_keeps_old_artifact(priced_data, monkeypatch, tmp_path):
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin, worker, group, site = priced_data
    material = WorkType.objects.get(code="material")
    tray = WorkType.objects.get(code="cable-tray")
    route = CableRoute.objects.create(code="priced-export-route", name_de="NH → HV")
    report = _accepted(admin, worker, site, date(2026, 9, 21), [
        _entry(worker, material, description="Lieferung", quantity=2, end=time(10, 30)),
        _entry(worker, tray, description="Trasse", route=route, start=time(11), end=time(12)),
    ])
    site.status = "completed"
    site.save(update_fields=["status"])
    first = generate_performance_report(actor=admin, group_id=group.pk)
    assert generate_performance_report(actor=admin, group_id=group.pk).pk == first.pk
    assert first.snapshot["sites"][0]["known_subtotal"] == "0.00"
    assert first.snapshot["sites"][0]["amount"] is None
    assert first.template_version != "ac-performance-6"
    with first.file.open("rb") as source:
        book = load_workbook(source)
    site_sheet = book.worksheets[1]
    tray_line = next(row for row in site_sheet.iter_rows(min_row=9) if str(row[0].value).startswith("Trasse"))
    delivery_line = next(row for row in site_sheet.iter_rows(min_row=9) if row[0].value == "Lieferung")
    assert tray_line[3].value == 0
    assert tray_line[4].data_type == "f"
    assert delivery_line[4].data_type == "f"
    assert "Teilbetrag" in " ".join(str(c.value) for row in book.active for c in row if c.value)

    corrected = save_report(
        actor=admin, report_id=report.pk, version=report.version, site=site,
        work_date=report.work_date, workforce=[worker], reason="Korrektur Lieferung",
        entries=[
            _entry(worker, material, description="Lieferung", quantity=2, end=time(12)),
            _entry(worker, tray, description="Trasse", route=route, start=time(12), end=time(13)),
        ],
    )
    assert corrected.status == "accepted"
    second = generate_performance_report(actor=admin, group_id=group.pk)
    assert second.pk != first.pk
    assert first.snapshot["sites"][0]["known_subtotal"] == "0.00"
    assert second.snapshot["sites"][0]["known_subtotal"] == "0.00"
    assert PerformanceExport.objects.count() == 2


def test_priced_summary_scope_does_not_mix_sites(priced_data):
    admin, worker, group, first = priced_data
    second = AcObject.objects.create(
        group=group, name="Haus 2", address="Straße 2", project_number="P-2", status="started"
    )
    material = WorkType.objects.get(code="material")
    _accepted(admin, worker, first, date(2026, 9, 21), [
        _entry(worker, material, description="Lieferung", end=time(10, 30))
    ])
    _accepted(admin, worker, second, date(2026, 9, 22), [
        _entry(worker, material, description="Lieferung", end=time(12))
    ])
    assert next(row for row in site_position_summary(first) if row.name == "Lieferung").amount == Decimal("0.00")
    assert next(row for row in site_position_summary(second) if row.name == "Lieferung").amount == Decimal("0.00")
    assert sum(row.amount or Decimal("0") for row in group_position_summary(group)) == Decimal("0.00")


def test_missing_current_accepted_snapshot_keeps_amount_incomplete(priced_data, monkeypatch, tmp_path):
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin, worker, group, site = priced_data
    material = WorkType.objects.get(code="material")
    report = _accepted(admin, worker, site, date(2026, 9, 21), [
        _entry(worker, material, description="Lieferung", end=time(10, 30))
    ])
    report.version += 1
    report.save(update_fields=["version"])
    site.status = "completed"
    site.save(update_fields=["status"])

    activity = site_activity_map([site.pk])[site.pk]
    assert activity.known_subtotal == 0
    assert activity.accepted_amount is None
    artifact = generate_performance_report(actor=admin, group_id=group.pk)
    assert artifact.snapshot["sites"][0]["amount"] is None
    assert artifact.snapshot["sites"][0]["excluded_reports"] == [report.pk]
    with artifact.file.open("rb") as source:
        book = load_workbook(source)
    assert "Teilbetrag" in " ".join(str(cell.value) for row in book.active for cell in row if cell.value)


def test_hourly_policy_requires_frozen_rule_and_agreed_code(priced_data):
    admin, worker, _group, site = priced_data
    material = WorkType.objects.get(code="material")
    other = WorkType.objects.create(
        code="priced-unknown-hour", name_de="Andere Stunden", direction="ac", unit="hour",
        calculation_rule="actual", price_mode="actual_hourly", unit_price=Decimal("40"),
    )
    _accepted(admin, worker, site, date(2026, 9, 21), [
        _entry(worker, material, description="Lieferung", end=time(9)),
        _entry(worker, other, description="Andere Stunden", start=time(10), end=time(11)),
    ])
    later = _accepted(admin, worker, site, date(2026, 9, 22), [
        _entry(worker, material, description="Lieferung", end=time(9)),
    ])
    revision = later.revisions.get(version=later.version)
    snapshot = revision.snapshot
    snapshot["entries"][0]["calculation_rule"] = "zero"
    revision.snapshot = snapshot
    revision.save(update_fields=["snapshot"])

    rows = site_position_summary(site)
    mixed = next(row for row in rows if row.name == "Lieferung")
    unknown = next(row for row in rows if row.name == "Andere Stunden")
    assert mixed.quantity == Decimal("2") and mixed.amount == Decimal("0.00")
    assert mixed.price_state == "unagreed"
    assert unknown.quantity == Decimal("1") and unknown.amount == Decimal("0.00")
    assert unknown.price_state == "unagreed"
