"""Структурированные позиции работ MBG и обзор Anlage."""

from datetime import time
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.urls import reverse
from django.utils import timezone
from features.mbg_reports.models import MbgWorkEntry
from features.mbg_reports.selectors import group_position_summary
from features.mbg_reports.services import save_report
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import CableRoute, CableType, WorkType

pytestmark = pytest.mark.django_db


def test_action_bar_is_centered_in_available_cabinet_width():
    css = Path("src/dlc_montage/features/mbg_reports/static/mbg_reports/css/editor.css").read_text(encoding="utf-8")

    assert "--mbg-shell-offset:var(--cab-sidebar-width)" in css
    assert "left:calc(var(--mbg-shell-offset) + (100vw - var(--mbg-shell-offset))/2)" in css
    assert ".cab-wrapper:has(.cab-sidebar--collapsed) .mbg-action-bar" in css
    assert "right:24px" not in css


@pytest.fixture
def position_data():
    admin = get_user_model().objects.create_user(username="positions-owner", is_superuser=True)
    people = [
        Employee.objects.create(first_name="Mykhailo", last_name="Abasov", has_ac_access=True),
        Employee.objects.create(first_name="Volodymyr", last_name="Malyshko", has_ac_access=True),
    ]
    group = ProjectGroup.objects.create(name="Aroser Allee", has_ac=True, has_dc=True)
    site = AcObject.objects.create(group=group, name="Haus 141", address="Aroser Allee 141", project_number="206")
    route = CableRoute.objects.create(code="test-wr-uv", name_de="WR → UV-PV", name_ru="WR → UV-PV")
    cable = CableType.objects.create(
        code="test-data-rj45",
        name_de="Datenleitung / RJ45",
        name_ru="Линия данных / RJ45",
        category="data",
        normative_hours_per_ten_meters=Decimal("1.50"),
    )
    return admin, people, group, site, route, cable


def test_cable_position_counts_quantity_once_for_several_participants(position_data):
    admin, people, _group, site, route, cable = position_data
    work = WorkType.objects.create(
        code="test-cable-laying",
        name_de="Kabelverlegung",
        name_ru="Прокладка кабеля",
        direction="ac",
        unit="ten_meters",
        calculation_rule="cable",
        price_mode="per_unit",
        unit_price=Decimal("60.00"),
    )

    report = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=people,
        entries=[
            {
                "participants": people,
                "starts_at": time(8),
                "ends_at": time(9),
                "work_type": work,
                "quantity": Decimal("2"),
                "cable_type": cable,
                "route": route,
                "standard_connections": 0,
                "heavy_connections": 0,
                "with_underconstruction": False,
                "description": "",
            }
        ],
    )

    entry = report.entries.get()
    assert list(entry.participants.order_by("pk")) == people
    assert entry.quantity == Decimal("2")
    assert entry.normative_person_hours == Decimal("3.00")
    assert entry.actual_person_hours == Decimal("2.00")
    assert entry.amount == Decimal("120.00")
    assert entry.description == "Kabelverlegung · WR → UV-PV · Datenleitung / RJ45 · × 2"  # noqa: RUF001
    assert report.revisions.get().snapshot["entries"][0]["description"] == entry.description


def test_description_roundtrip_keeps_custom_text_and_replaces_structured_details(position_data, client):
    admin, people, _group, site, route, cable = position_data
    work = WorkType.objects.create(
        code="test-description-cable",
        name_de="Kabelverlegung",
        name_ru="Прокладка кабеля",
        direction="ac",
        unit="ten_meters",
        calculation_rule="cable",
        price_mode="per_unit",
        unit_price=Decimal("60.00"),
    )
    row = {
        "participants": [people[0]],
        "starts_at": time(8),
        "ends_at": time(9),
        "work_type": work,
        "quantity": Decimal("2"),
        "cable_type": cable,
        "route": route,
        "standard_connections": 0,
        "heavy_connections": 0,
        "with_underconstruction": False,
        "description": "WR1: Kabel zum Verteiler",
    }
    report = save_report(
        actor=admin, site=site, work_date=timezone.localdate(), workforce=[people[0]], entries=[row]
    )
    first_description = report.entries.get().description
    assert first_description == "WR1: Kabel zum Verteiler · WR → UV-PV · Datenleitung / RJ45 · × 2"  # noqa: RUF001
    assert report.entries.get().custom_description == "WR1: Kabel zum Verteiler"

    client.force_login(admin)
    response = client.get(reverse("mbg_reports:edit", args=[report.pk]))
    assert response.context["formset"].forms[0].initial["description"] == "WR1: Kabel zum Verteiler"

    saved = client.post(
        reverse("mbg_reports:edit", args=[report.pk]),
        {
            "action": "save",
            "group": str(site.group_id),
            "site": str(site.pk),
            "work_date": str(report.work_date),
            "workforce": [str(people[0].pk)],
            "version": str(report.version),
            "submission_key": str(report.submission_key),
            "entries-TOTAL_FORMS": "1",
            "entries-INITIAL_FORMS": "1",
            "entries-MIN_NUM_FORMS": "1",
            "entries-MAX_NUM_FORMS": "100",
            "entries-0-participants": [str(people[0].pk)],
            "entries-0-starts_at": "08:00",
            "entries-0-ends_at": "09:00",
            "entries-0-work_type": str(work.pk),
            "entries-0-quantity": "2",
            "entries-0-cable_type": str(cable.pk),
            "entries-0-route": str(route.pk),
            "entries-0-standard_connections": "0",
            "entries-0-heavy_connections": "0",
            "entries-0-description": response.context["formset"].forms[0].initial["description"],
        },
    )
    assert saved.status_code == 302
    report.refresh_from_db()
    assert report.entries.get().description == first_description

    report = save_report(
        actor=admin,
        report_id=report.pk,
        version=report.version,
        site=site,
        work_date=timezone.localdate(),
        workforce=[people[0]],
        entries=[{**row, "quantity": Decimal("3"), "description": "WR1: Kabel zum Verteiler"}],
    )
    assert report.entries.get().description == "WR1: Kabel zum Verteiler · WR → UV-PV · Datenleitung / RJ45 · × 3"  # noqa: RUF001
    assert report.entries.get().custom_description == "WR1: Kabel zum Verteiler"
    assert report.revisions.first().snapshot["entries"][0]["custom_description"] == "WR1: Kabel zum Verteiler"

    other_route = CableRoute.objects.create(code="test-wr2-uv", name_de="WR2 → UV-PV")
    other_cable = CableType.objects.create(
        code="test-power-description",
        name_de="Leistungskabel 5×10",  # noqa: RUF001
        category="power",
        normative_hours_per_ten_meters=Decimal("1.50"),
    )
    report = save_report(
        actor=admin,
        report_id=report.pk,
        version=report.version,
        site=site,
        work_date=timezone.localdate(),
        workforce=[people[0]],
        entries=[
            {
                **row,
                "route": other_route,
                "cable_type": other_cable,
                "quantity": Decimal("1"),
                "description": "WR1: Kabel zum Verteiler",
            }
        ],
    )
    assert report.entries.get().description == "WR1: Kabel zum Verteiler · WR2 → UV-PV · Leistungskabel 5×10"  # noqa: RUF001


def test_description_backfill_removes_only_known_generated_suffix(position_data):
    admin, people, _group, site, route, cable = position_data
    work = WorkType.objects.create(
        code="test-description-backfill",
        name_de="Kabelverlegung",
        name_ru="Прокладка кабеля",
        direction="ac",
        unit="ten_meters",
        calculation_rule="cable",
        price_mode="per_unit",
        unit_price=Decimal("60.00"),
    )
    prose = "WR2: WR → UV-PV ist bereits vorbereitet"
    base_row = {
        "participants": [people[0]],
        "starts_at": time(8),
        "ends_at": time(9),
        "work_type": work,
        "quantity": Decimal("2"),
        "cable_type": cable,
        "route": route,
        "standard_connections": 0,
        "heavy_connections": 0,
        "with_underconstruction": False,
        "description": prose,
    }
    report = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=[people[0]],
        entries=[
            base_row,
            {**base_row, "starts_at": time(9), "ends_at": time(10), "description": ""},
            {**base_row, "starts_at": time(10), "ends_at": time(11), "description": "Unklare Beschreibung"},
        ],
    )
    entry, automatic, ambiguous = list(report.entries.all())
    revision_snapshot = report.revisions.get().snapshot
    MbgWorkEntry.objects.filter(report=report).update(custom_description="")
    MbgWorkEntry.objects.filter(pk=ambiguous.pk).update(description="Unklare historische Zeile")

    migration = import_module("features.mbg_reports.migrations.0009_mbgworkentry_custom_description")
    historical_apps = MigrationLoader(connection).project_state(
        ("mbg_reports", "0009_mbgworkentry_custom_description")
    ).apps
    migration.backfill_custom_descriptions(historical_apps, SimpleNamespace(connection=connection))

    entry.refresh_from_db()
    automatic.refresh_from_db()
    ambiguous.refresh_from_db()
    assert entry.custom_description == prose
    assert entry.description == f"{prose} · WR → UV-PV · Datenleitung / RJ45 · × 2"  # noqa: RUF001
    assert automatic.custom_description == ""
    assert ambiguous.custom_description == "Unklare historische Zeile"
    assert report.revisions.get().snapshot == revision_snapshot


def test_description_replaces_construction_and_connection_details(position_data):
    admin, people, _group, site, _route, _cable = position_data
    work = WorkType.objects.create(
        code="test-description-connections",
        name_de="Anschlüsse",
        name_ru="Подключения",
        direction="ac",
        calculation_rule="connection",
        price_mode="per_norm_hour",
        unit_price=Decimal("40.00"),
    )
    row = {
        "participants": [people[0]],
        "starts_at": time(8),
        "ends_at": time(9),
        "work_type": work,
        "quantity": Decimal("1"),
        "cable_type": None,
        "route": None,
        "standard_connections": 3,
        "heavy_connections": 2,
        "with_underconstruction": True,
        "description": "WR2: Anschlussarbeiten",
    }
    report = save_report(
        actor=admin, site=site, work_date=timezone.localdate(), workforce=[people[0]], entries=[row]
    )
    assert report.entries.get().description == (
        "WR2: Anschlussarbeiten · mit Unterkonstruktion · 3 Standardanschlüsse · 2 Schweranschlüsse"
    )

    report = save_report(
        actor=admin,
        report_id=report.pk,
        version=report.version,
        site=site,
        work_date=timezone.localdate(),
        workforce=[people[0]],
        entries=[
            {
                **row,
                "standard_connections": 2,
                "heavy_connections": 0,
                "with_underconstruction": False,
            }
        ],
    )
    assert report.entries.get().description == "WR2: Anschlussarbeiten · 2 Standardanschlüsse"


def test_route_is_included_in_automatic_cable_tray_description(position_data):
    admin, people, _group, site, route, _cable = position_data
    work = WorkType.objects.create(
        code="test-cable-tray",
        name_de="Montage Kabeltrasse",
        name_ru="Монтаж кабельной трассы",
        calculation_rule="fixed",
        normative_hours=Decimal("2.00"),
        price_mode="per_unit",
        unit_price=Decimal("80.00"),
    )

    report = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=people,
        entries=[
            {
                "participants": people,
                "starts_at": time(8),
                "ends_at": time(9),
                "work_type": work,
                "quantity": Decimal("1"),
                "cable_type": None,
                "route": route,
                "standard_connections": 0,
                "heavy_connections": 0,
                "with_underconstruction": False,
                "description": "",
            }
        ],
    )

    assert report.entries.get().description == "Montage Kabeltrasse · WR → UV-PV"


def test_cable_tray_requires_route(position_data):
    admin, people, _group, site, _route, _cable = position_data
    work = WorkType.objects.get(code="cable-tray")

    with pytest.raises(ValidationError, match="путь"):
        save_report(
            actor=admin,
            site=site,
            work_date=timezone.localdate(),
            workforce=people,
            entries=[
                {
                    "participants": people,
                    "starts_at": time(8),
                    "ends_at": time(9),
                    "work_type": work,
                    "quantity": Decimal("1"),
                    "cable_type": None,
                    "route": None,
                    "standard_connections": 0,
                    "heavy_connections": 0,
                    "with_underconstruction": False,
                    "description": "",
                }
            ],
        )


def test_connection_uses_shared_preparation_and_progressive_cable_time(position_data):
    admin, people, _group, site, _route, _cable = position_data
    work = WorkType.objects.create(
        code="cable-connection",
        name_de="Kabelanschluss",
        name_ru="Подключение кабелей",
        calculation_rule="connection",
        price_mode="per_norm_hour",
        unit_price=Decimal("40.00"),
    )

    report = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=people,
        entries=[
            {
                "participants": [people[0]],
                "starts_at": time(9),
                "ends_at": time(10, 15),
                "work_type": work,
                "quantity": Decimal("1"),
                "cable_type": None,
                "route": None,
                "standard_connections": 2,
                "heavy_connections": 1,
                "with_underconstruction": False,
                "description": "Anschluss UV-PV",
            }
        ],
    )

    entry = report.entries.get()
    assert entry.normative_person_hours == Decimal("1.25")
    assert entry.amount == Decimal("50.00")


def test_group_summary_contains_performed_and_zero_catalog_positions(position_data):
    admin, people, group, site, _route, _cable = position_data
    performed = WorkType.objects.create(
        code="wr-mount-new",
        name_de="Montage Wechselrichter",
        name_ru="Монтаж инвертора",
        calculation_rule="fixed",
        normative_hours=Decimal("1.00"),
        price_mode="per_unit",
        unit_price=Decimal("40.00"),
        sort_order=1,
    )
    unused = WorkType.objects.create(
        code="uv-mount-new",
        name_de="Montage UV-PV",
        name_ru="Монтаж UV-PV",
        calculation_rule="fixed",
        normative_hours=Decimal("1.00"),
        price_mode="per_unit",
        unit_price=Decimal("40.00"),
        sort_order=2,
    )
    report = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=people,
        entries=[
            {
                "participants": people,
                "starts_at": time(10),
                "ends_at": time(11),
                "work_type": performed,
                "quantity": Decimal("1"),
                "cable_type": None,
                "route": None,
                "standard_connections": 0,
                "heavy_connections": 0,
                "with_underconstruction": False,
                "description": "",
            }
        ],
        submit=True,
    )
    from features.mbg_reports.services import review_report

    review_report(actor=admin, report_id=report.pk, version=report.version, decision="accept")

    rows = {row.code: row for row in group_position_summary(group)}
    assert rows[performed.code].quantity is None
    assert rows[performed.code].actual_person_hours == Decimal("2.00")
    assert rows[performed.code].amount is None
    assert rows[unused.code].quantity == Decimal("0")
    assert rows[unused.code].amount == Decimal("0")


def test_old_single_employee_contract_is_removed():
    with pytest.raises(FieldDoesNotExist):
        MbgWorkEntry._meta.get_field("employee")


def test_position_form_and_group_overview_are_available(position_data, client):
    admin, _people, group, _site, _route, _cable = position_data
    client.force_login(admin)

    form_response = client.get(reverse("mbg_reports:new"))
    overview_response = client.get(reverse("mbg_reports:group_overview", args=[group.pk]))

    assert form_response.status_code == 200
    assert 'name="group"' in form_response.content.decode()
    assert 'hx-get="/ru/cabinet/ac/mbg-reports/site-options/"' in form_response.content.decode()
    assert 'data-availability-url="/ru/cabinet/ac/mbg-reports/employee-availability/"' in form_response.content.decode()
    assert "data-mbg-action-bar" in form_response.content.decode()
    assert 'name="site"' in form_response.content.decode()
    assert 'Haus 141' not in form_response.content.decode()
    assert 'name="workforce"' in form_response.content.decode()
    assert 'data-day-workforce' in form_response.content.decode()
    assert 'name="entries-0-participants"' in form_response.content.decode()
    assert 'data-entry-participants' in form_response.content.decode()
    assert 'name="entries-0-quantity"' in form_response.content.decode()
    assert 'name="entries-0-cable_type"' in form_response.content.decode()
    assert 'name="entries-0-route"' in form_response.content.decode()
    assert 'data-requires-route="true"' in form_response.content.decode()
    assert 'data-requires-cable="true"' in form_response.content.decode()
    assert overview_response.status_code == 200
    assert "Montage Wechselrichter" in overview_response.content.decode()


def test_position_participants_must_belong_to_selected_day_workforce(position_data):
    admin, people, _group, site, _route, _cable = position_data
    work = WorkType.objects.get(code="wr-montage")

    with pytest.raises(ValidationError, match="состава рабочего дня"):
        save_report(
            actor=admin,
            site=site,
            work_date=timezone.localdate(),
            workforce=[people[0]],
            entries=[
                {
                    "participants": [people[1]],
                    "starts_at": time(8),
                    "ends_at": time(9),
                    "work_type": work,
                    "quantity": Decimal("1"),
                    "cable_type": None,
                    "route": None,
                    "standard_connections": 0,
                    "heavy_connections": 0,
                    "with_underconstruction": False,
                    "description": "",
                }
            ],
        )


def test_multiday_unlinked_work_on_same_route_keeps_both_quantities_unresolved(position_data):
    from datetime import timedelta

    from features.mbg_reports.selectors import site_position_summary

    admin, people, _group, site, route, _cable = position_data
    work = WorkType.objects.get(code="cable-tray")

    # Day 1: 0.5 hours on route
    first = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate() - timedelta(days=1),
        workforce=[people[0]],
        entries=[
            {
                "participants": [people[0]],
                "starts_at": time(16, 30),
                "ends_at": time(17, 0),
                "work_type": work,
                "quantity": Decimal("1"),
                "cable_type": None,
                "route": route,
                "standard_connections": 0,
                "heavy_connections": 0,
                "with_underconstruction": False,
                "description": "Part 1",
            }
        ],
        submit=True,
    )
    from features.mbg_reports.services import review_report

    review_report(actor=admin, report_id=first.pk, version=first.version, decision="accept")

    # Day 2: 1.5 hours on the SAME route
    second = save_report(
        actor=admin,
        site=site,
        work_date=timezone.localdate(),
        workforce=[people[0]],
        entries=[
            {
                "participants": [people[0]],
                "starts_at": time(10, 0),
                "ends_at": time(11, 30),
                "work_type": work,
                "quantity": Decimal("1"),
                "cable_type": None,
                "route": route,
                "standard_connections": 0,
                "heavy_connections": 0,
                "with_underconstruction": False,
                "description": "Part 2",
            }
        ],
        submit=True,
    )
    review_report(actor=admin, report_id=second.pk, version=second.version, decision="accept")

    summary = site_position_summary(site)
    tray_rows = [r for r in summary if r.code == "cable-tray" and r.sources]

    assert len(tray_rows) == 2
    assert all(row.quantity is None and row.amount is None for row in tray_rows)
    assert sum((row.actual_person_hours for row in tray_rows), Decimal("0")) == Decimal("2.00")
