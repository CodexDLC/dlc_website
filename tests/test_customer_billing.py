"""Customer packages close from physical work, without rewriting time or history."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from features.mbg_reports.customer_billing_selectors import customer_billing_summary
from features.mbg_reports.customer_billing_services import prepare_customer_packages, save_customer_package
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.projects.services import save_site_work_item
from features.staff.models import Employee
from features.work_catalog.models import CableRoute, CableType, CustomerWorkPosition, WorkType
from openpyxl import load_workbook

pytestmark = pytest.mark.django_db


@pytest.fixture
def billing_data():
    actor = get_user_model().objects.create_user(username="customer-billing-owner", is_superuser=True)
    worker = Employee.objects.create(first_name="Ada", last_name="Montage", has_ac_access=True)
    group = ProjectGroup.objects.create(name="Customer packages")
    site = AcObject.objects.create(group=group, name="Haus", address="Straße 1", project_number="P-1", status="started")
    return actor, worker, site


def item(actor, site, code, label, **kwargs):
    return save_site_work_item(
        actor=actor,
        site=site,
        work_type=WorkType.objects.get(code=code),
        label=label,
        planned_quantity=kwargs.pop("planned_quantity", 1),
        **kwargs,
    )


def accept(actor, worker, site, day, items):
    entries = []
    for number, (work_item, delta) in enumerate(items):
        entries.append(
            {
                "participants": [worker],
                "starts_at": time(8 + number),
                "ends_at": time(9 + number),
                "work_type": work_item.work_type,
                "work_item": work_item,
                "completed_quantity": Decimal(str(delta)),
                "quantity": Decimal("1"),
                "route": work_item.route,
                "cable_type": work_item.cable_type,
                "standard_connections": 1 if work_item.work_type.calculation_rule == "connection" else 0,
                "heavy_connections": 0,
                "with_underconstruction": work_item.with_underconstruction,
            }
        )
    report = save_report(actor=actor, site=site, work_date=day, workforce=[worker], entries=entries, submit=True)
    return review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")


def row(summary, code):
    return next(r for r in summary.rows if r.code == code)


def test_uv_package_closes_once_across_days_preserving_accepted_snapshots(billing_data):
    actor, worker, site = billing_data
    mount = item(actor, site, "uv-montage", "UV")
    connect = item(actor, site, "uv-anschluss", "UV Anschluss")
    prepare_customer_packages(actor=actor, site=site)
    first = accept(actor, worker, site, date(2026, 11, 1), [(mount, 1)])
    snapshot = first.revisions.get(version=first.version).snapshot
    assert row(customer_billing_summary(site), "10.010").quantity == 0
    accept(actor, worker, site, date(2026, 11, 2), [(connect, 1)])
    summary = customer_billing_summary(site)
    assert row(summary, "10.010").quantity == 1
    assert row(summary, "10.010").amount == Decimal("60.00")
    assert summary.known_subtotal == Decimal("60.00")
    assert summary.amount == Decimal("60.00")
    assert len(row(summary, "10.010").sources) == 2
    prepare_customer_packages(actor=actor, site=site)
    assert row(customer_billing_summary(site), "10.010").amount == Decimal("60.00")
    assert first.revisions.get(version=first.version).snapshot == snapshot


def test_two_parallel_power_cables_and_tray_make_one_explicit_route_package(billing_data):
    actor, worker, site = billing_data
    route = CableRoute.objects.get(code="nh-new-hv")
    cable = CableType.objects.get(code="power-5x16")
    power1 = item(actor, site, "cable-laying", "NH-HV 1", route=route, cable_type=cable, planned_quantity=2)
    power2 = item(actor, site, "cable-laying", "NH-HV 2", route=route, cable_type=cable, planned_quantity=2)
    tray = item(actor, site, "cable-tray", "NH-HV Trasse", route=route, planned_quantity=2)
    save_customer_package(
        actor=actor,
        site=site,
        position=CustomerWorkPosition.objects.get(code="01.0160"),
        label="NH-HV",
        quantity=2,
        items=[power1, power2, tray],
        note="Gemeinsamer Weg bis 20 m",
    )
    accept(actor, worker, site, date(2026, 11, 1), [(power1, 2), (power2, 2)])
    assert row(customer_billing_summary(site), "01.0160").quantity == 0
    accept(actor, worker, site, date(2026, 11, 2), [(tray, 2)])
    result = row(customer_billing_summary(site), "01.0160")
    assert result.quantity == 2 and result.amount == Decimal("140.00")


def test_manual_positions_need_quantity_confirmation_and_reason(billing_data):
    actor, _worker, site = billing_data
    position = CustomerWorkPosition.objects.get(code="01.0200")
    with pytest.raises(ValidationError):
        save_customer_package(
            actor=actor,
            site=site,
            position=position,
            label="Com.Box",
            quantity=3,
            items=[],
            manual_confirmed=True,
            note="",
        )
    save_customer_package(
        actor=actor,
        site=site,
        position=position,
        label="Com.Box",
        quantity=3,
        items=[],
        manual_confirmed=True,
        note="Aufmaß manuell bestätigt",
    )
    result = row(customer_billing_summary(site), "01.0200")
    assert result.quantity == 3 and result.amount == Decimal("25.50")
    assert result.unit == "Einheit ungeklärt"


def test_cross_site_components_duplicate_billing_and_unauthorized_writes_rejected(billing_data):
    actor, _worker, site = billing_data
    mount = item(actor, site, "wr-montage", "WR1")
    position = CustomerWorkPosition.objects.get(code="01.0020")
    save_customer_package(actor=actor, site=site, position=position, label="WR1", quantity=1, items=[mount])
    with pytest.raises(ValidationError):
        save_customer_package(
            actor=actor, site=site, position=position, label="WR1 duplicate", quantity=1, items=[mount]
        )
    other = AcObject.objects.create(group=site.group, name="Other")
    with pytest.raises(ValidationError):
        save_customer_package(actor=actor, site=other, position=position, label="Wrong site", quantity=1, items=[mount])
    user = get_user_model().objects.create_user(username="billing-not-owner")
    with pytest.raises(PermissionDenied):
        prepare_customer_packages(actor=user, site=site)


def test_patch_is_unmapped_and_missing_accepted_snapshot_blocks_final_amount(billing_data):
    actor, worker, site = billing_data
    patch = item(
        actor,
        site,
        "cable-laying",
        "Patch",
        route=CableRoute.objects.get(code="wr-uv"),
        cable_type=CableType.objects.get(code="data"),
    )
    report = accept(actor, worker, site, date(2026, 11, 1), [(patch, 1)])
    prepare_customer_packages(actor=actor, site=site)
    summary = customer_billing_summary(site)
    assert any(r.work_item_id == patch.pk for r in summary.unmapped_rows)
    assert row(summary, "01.0200").quantity == 0
    assert summary.amount is None
    report.version += 1
    report.save(update_fields=["version"])
    summary = customer_billing_summary(site)
    assert summary.amount is None and report.pk in summary.excluded_reports


def test_customer_export_uses_original_codes_and_real_amounts_and_freezes_prices(billing_data, monkeypatch, tmp_path):
    from features.mbg_reports.exports import generate_performance_report
    from features.mbg_reports.models import PerformanceExport

    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    actor, worker, site = billing_data
    mount = item(actor, site, "uv-montage", "UV")
    connect = item(actor, site, "uv-anschluss", "UV Anschluss")
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connect, 1)])
    site.status = "completed"
    site.save(update_fields=["status"])
    export = generate_performance_report(actor=actor, group_id=site.group_id)
    assert export.snapshot["sites"][0]["known_subtotal"] == "60.00"
    assert export.snapshot["sites"][0]["amount"] == "60.00"

    uv = next(r for r in export.snapshot["sites"][0]["rows"] if r["code"] == "10.010")
    assert uv["quantity"] == "1.00" and uv["unit_price"] == "60.00"
    with export.file.open("rb") as source:
        book = load_workbook(source)
    assert any("10.010" in str(c.value) for r in book.worksheets[1] for c in r)
    position = CustomerWorkPosition.objects.get(code="10.010")
    position.unit_price = Decimal("65")
    position.save(update_fields=["unit_price"])
    revised = generate_performance_report(actor=actor, group_id=site.group_id)
    assert revised.pk != export.pk
    assert revised.snapshot["sites"][0]["amount"] == "65.00"
    export.refresh_from_db()
    assert export.snapshot["sites"][0]["amount"] == "60.00"


def test_device_package_bills_each_finished_device_in_aggregate_plan(billing_data):
    actor, worker, site = billing_data
    mount = item(actor, site, "uv-montage", "UV 1+2", planned_quantity=2)
    connect = item(actor, site, "uv-anschluss", "UV 1+2 Anschluss", planned_quantity=2)
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connect, 1)])
    summary = customer_billing_summary(site)
    assert row(summary, "10.010").quantity == 1
    assert summary.known_subtotal == Decimal("60.00")
    assert summary.amount is None
    accept(actor, worker, site, date(2026, 11, 2), [(mount, 1), (connect, 1)])
    assert customer_billing_summary(site).amount == Decimal("120.00")


def test_inactive_position_package_can_be_retired_after_plan_change(billing_data):
    actor, worker, site = billing_data
    mount = item(actor, site, "uv-montage", "UV")
    connect = item(actor, site, "uv-anschluss", "UV Anschluss")
    package = prepare_customer_packages(actor=actor, site=site)[0]
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connect, 1)])
    assert customer_billing_summary(site).known_subtotal == Decimal("60.00")
    position = package.position
    position.is_active = False
    position.save(update_fields=["is_active"])
    mount.planned_quantity = 2
    mount.is_required = False
    mount.save(update_fields=["planned_quantity", "is_required"])
    assert customer_billing_summary(site).known_subtotal == 0
    save_customer_package(
        actor=actor,
        site=site,
        position=position,
        label=package.label,
        quantity=1,
        items=[mount, connect],
        note="Veraltete Zuordnung stillgelegt",
        is_active=False,
        pk=package.pk,
    )
    assert not customer_billing_summary(site).packages


def test_curator_reporting_recognizes_customer_catalogue_acceptance(billing_data):
    from features.customer_portal.models import ClientMembership
    from features.customer_portal.services import decide_review, submit_for_review
    from features.mbg_reports.reporting_selectors import resolve_curator_review
    from features.projects.models import Client

    actor, worker, site = billing_data
    customer = get_user_model().objects.create_user(username="curator-customer")
    company = Client.objects.create(name="Curator company")
    site.group.client = company
    site.group.save(update_fields=["client"])
    ClientMembership.objects.create(user=customer, client=company, granted_by=actor)
    mount = item(actor, site, "uv-montage", "UV")
    connect = item(actor, site, "uv-anschluss", "UV Anschluss")
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connect, 1)])
    site.status = "completed"
    site.save(update_fields=["status"])
    review = submit_for_review(actor=actor, site=site)
    decide_review(
        actor=customer,
        site=site,
        decisions={r["key"]: {"decision": "accepted", "comment": ""} for r in review.work_snapshot},
        snapshot_digest=review.snapshot_digest,
        submission_token=review.submitted_at.isoformat(),
    )
    assert resolve_curator_review(site).status == "Freigegeben"
    assert resolve_curator_review(site).freigabe == "Nein"
    position = CustomerWorkPosition.objects.get(code="10.010")
    position.unit_price = 65
    position.save(update_fields=["unit_price"])
    assert resolve_curator_review(site).status == "Freigegeben"
    package = site.customer_work_packages.get(position=position)
    package.quantity = 2
    package.save(update_fields=["quantity"])
    assert resolve_curator_review(site).status == "In Prüfung"


def test_generic_other_work_is_not_automatically_billable_extra_hours(billing_data):
    actor, worker, site = billing_data
    work = WorkType.objects.get(code="sonstige")
    report = save_report(
        actor=actor,
        site=site,
        work_date=date(2026, 11, 1),
        workforce=[worker],
        submit=True,
        entries=[
            {
                "participants": [worker],
                "starts_at": time(8),
                "ends_at": time(9),
                "work_type": work,
                "description": "Verlegung PE-Leitung Tiefenerder → HPAS",
                "quantity": Decimal("1"),
            }
        ],
    )
    review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")
    summary = customer_billing_summary(site)
    assert row(summary, "01.0090").quantity == 0
    assert summary.known_subtotal == 0
    assert not summary.unmapped_rows
    assert summary.amount == Decimal("0.00")


def test_nh_mount_and_connection_count_separately_without_daily_duplication(billing_data):
    from features.customer_portal.customer_position_snapshot import customer_position_snapshot

    actor, worker, site = billing_data
    mount = item(actor, site, "nh-montage", "NH Montage")
    connect = item(actor, site, "nh-anschluss", "NH Anschluss")
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1)])
    assert row(customer_billing_summary(site), "01.0060").quantity == 1
    accept(actor, worker, site, date(2026, 11, 2), [(connect, 1)])
    assert row(customer_billing_summary(site), "01.0060").amount == Decimal("60.00")
    prepare_customer_packages(actor=actor, site=site)
    assert row(customer_billing_summary(site), "01.0060").quantity == 2
    assert (
        "Zusätzliches Kabel"
        not in next(r for r in customer_position_snapshot(site, include_unperformed=True) if r["code"] == "01.0060")[
            "name_de"
        ]
    )


def test_nh_existing_extension_is_separate_customer_review_quantity(billing_data):
    from features.customer_portal.customer_position_snapshot import customer_position_snapshot

    actor, worker, site = billing_data
    mount = item(actor, site, "nh-montage", "NH Montage")
    connection = item(actor, site, "nh-anschluss", "NH Anschluss")
    extension = item(
        actor,
        site,
        "cable-laying",
        "NH extension",
        route=CableRoute.objects.create(code="nh-existing-cable-extension", name_de="Bestandsleitung verlängern"),
        cable_type=CableType.objects.get(code="power-5x16"),
    )
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connection, 1)])
    before = next(r for r in customer_position_snapshot(site, include_unperformed=True) if r["code"] == "01.0060")
    assert before["quantity"] == "2.00" and "Zusätzliches Kabel" not in before["name_de"]
    accept(actor, worker, site, date(2026, 11, 2), [(extension, 1)])
    result = row(customer_billing_summary(site), "01.0060")
    assert result.quantity == 3 and result.amount == Decimal("90.00")
    entry = next(r for r in customer_position_snapshot(site, include_unperformed=True) if r["code"] == "01.0060")
    assert "Zusätzliches Kabel zur Verlängerung der Bestandsleitung" in entry["name_de"]


def test_manager_prepares_unambiguous_packages_but_cannot_edit_financial_packages(billing_data):
    from django.contrib.auth.models import Permission

    actor, _worker, site = billing_data
    manager = get_user_model().objects.create_user(username="limited-billing-manager")
    manager.user_permissions.add(
        Permission.objects.get(codename="manage_reports", content_type__app_label="internal_time")
    )
    mount = item(actor, site, "uv-montage", "UV Manager")
    connect = item(actor, site, "uv-anschluss", "UV Manager Anschluss")
    packages = prepare_customer_packages(actor=manager, site=site)
    assert len(packages) == 1 and packages[0].position.code == "10.010"
    assert set(packages[0].work_items.values_list("pk", flat=True)) == {mount.pk, connect.pk}
    assert prepare_customer_packages(actor=manager, site=site) == ()
    with pytest.raises(PermissionDenied):
        save_customer_package(
            actor=manager,
            site=site,
            position=packages[0].position,
            label="changed",
            quantity=1,
            items=[mount, connect],
            pk=packages[0].pk,
        )
    packages[0].refresh_from_db()
    assert packages[0].label == "UV-PV"


def test_manager_submission_prepares_completed_work_instead_of_zero_catalog(billing_data):
    from django.contrib.auth.models import Permission
    from features.customer_portal.services import submit_for_review
    from features.mbg_reports.models import CustomerWorkPackage
    from features.projects.models import Client

    actor, worker, site = billing_data
    mount = item(actor, site, "uv-montage", "UV")
    connect = item(actor, site, "uv-anschluss", "UV Anschluss")
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connect, 1)])
    site.group.client = Client.objects.create(name="Submission preparation customer")
    site.group.save()
    site.status = "completed"
    site.save()
    manager = get_user_model().objects.create_user(username="submission-limited-manager")
    manager.user_permissions.add(
        Permission.objects.get(codename="manage_reports", content_type__app_label="internal_time")
    )
    assert not CustomerWorkPackage.objects.filter(site=site).exists()
    review = submit_for_review(actor=manager, site=site)
    uv = next(r for r in review.work_snapshot if r["code"] == "10.010")
    assert uv["quantity"] == "1.00"
    assert len(review.work_snapshot) == 21
    assert CustomerWorkPackage.objects.filter(site=site).count() == 1


def test_delivery_flat_is_once_per_site_across_days_without_reducing_time(billing_data):
    actor, worker, site = billing_data
    work = WorkType.objects.get(code="material-delivery")
    reports = []
    for day in [date(2026, 11, 1), date(2026, 11, 2)]:
        report = save_report(
            actor=actor,
            site=site,
            work_date=day,
            workforce=[worker],
            entries=[
                {
                    "participants": [worker],
                    "starts_at": time(8),
                    "ends_at": time(9),
                    "work_type": work,
                    "quantity": Decimal("1"),
                }
            ],
            submit=True,
        )
        reports.append(review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept"))
    result = row(customer_billing_summary(site), "01.0110")
    assert result.quantity == 1 and result.amount == Decimal("55.00")
    assert len(result.sources) == 2
    assert sum(report.entries.get().actual_person_hours for report in reports) == Decimal("2.00")


def test_two_nh_devices_in_aggregate_bill_each_completed_mount_and_connection(billing_data):
    actor, worker, site = billing_data
    mount = item(actor, site, "nh-montage", "NH 1+2 Montage", planned_quantity=2)
    connection = item(actor, site, "nh-anschluss", "NH 1+2 Anschluss", planned_quantity=2)
    prepare_customer_packages(actor=actor, site=site)
    accept(actor, worker, site, date(2026, 11, 1), [(mount, 1), (connection, 1)])
    assert row(customer_billing_summary(site), "01.0060").amount == Decimal("60.00")
    accept(actor, worker, site, date(2026, 11, 2), [(mount, 1), (connection, 1)])
    assert row(customer_billing_summary(site), "01.0060").amount == Decimal("120.00")
