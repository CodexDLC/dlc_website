"""Контракт единого каталога работ AC и DC."""

from datetime import time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from features.mbg_reports.calculations import calculate_position
from features.work_catalog.forms import WorkTypeForm
from features.work_catalog.models import CableRoute, WorkType
from features.work_catalog.services import save_work_type

pytestmark = pytest.mark.django_db


def test_shared_work_type_is_available_in_both_directions():
    work = WorkType.objects.create(
        code="shared-material-delivery",
        name_de="Materialtransport",
        name_ru="Доставка материала",
        direction="both",
        unit="flat",
    )

    assert work in WorkType.objects.for_direction("ac")
    assert work in WorkType.objects.for_direction("dc")


def test_work_type_form_and_service_persist_commercial_unit():
    admin = get_user_model().objects.create_user(username="catalog-admin", is_superuser=True)
    form = WorkTypeForm(
        data={
            "code": "dc-montage-kwp",
            "name_de": "DC-Montage nach kWp",
            "name_ru": "DC-монтаж по мощности",
            "direction": "dc",
            "unit": "kwp",
            "calculation_rule": "fixed",
            "normative_hours": "1.00",
            "price_mode": "per_unit",
            "unit_price": "40.00",
            "underconstruction_hours": "0.00",
            "is_break": False,
            "sort_order": 10,
            "is_active": True,
        }
    )

    assert form.is_valid(), form.errors
    work = save_work_type(actor=admin, data=form.cleaned_data)

    assert work.direction == "dc"
    assert work.unit == "kwp"


def test_seeded_mbg_positions_remain_ac_only():
    work = WorkType.objects.get(code="nh-montage")

    assert work.direction == "ac"


def test_potential_bonding_bar_connection_is_seeded():
    work = WorkType.objects.get(code="hpas-anschluss")

    assert work.name_de == "Anschluss an die Potentialausgleichsschiene"
    assert work.name_ru == "Подключение к шине уравнивания потенциалов"
    assert work.direction == "ac"
    assert work.unit == "piece"
    assert work.calculation_rule == "connection"
    assert work.price_mode == "per_unit"
    assert work.unit_price == Decimal("20.00")


def test_photo_documentation_tracks_time_without_payment():
    work = WorkType.objects.get(code="photo-documentation")

    totals = calculate_position(
        work_type=work,
        starts_at=time(15),
        ends_at=time(16, 30),
        participant_count=1,
        quantity=1,
    )

    assert work.name_de == "Erstellung der Fotodokumentation"
    assert work.name_ru == "Фотодокументация выполненных работ"
    assert work.calculation_rule == "zero"
    assert work.price_mode == "zero"
    assert totals.actual_person_hours == 1.5
    assert totals.normative_person_hours == 1.5
    assert totals.amount == 0


def test_uv_to_new_hpas_route_is_seeded():
    route = CableRoute.objects.get(code="uv-hpas-new")

    assert route.name_de == "UV-PV → neue HPAS"
    assert route.name_ru == "UV-PV → новая HPAS"
    assert route.is_active


def test_material_delivery_pays_fixed_50_eur_regardless_of_hours_or_crew():
    work = WorkType.objects.get(code="material-delivery")

    assert work.name_de == "Materialabholung und Anlieferung"
    assert work.name_ru == "Заезд и доставка материала"
    assert work.unit == "flat"
    assert work.calculation_rule == "fixed"
    assert work.price_mode == "per_unit"
    assert work.unit_price == Decimal("50.00")
    assert work.is_active is True

    # 3 hours, 2 participants -> 6 person-hours in Stundennachweis, but exactly 50 € flat fee!
    totals = calculate_position(
        work_type=work,
        starts_at=time(8),
        ends_at=time(11),
        participant_count=2,
        quantity=Decimal("1"),
    )
    assert totals.actual_person_hours == Decimal("6.00")
    assert totals.amount == Decimal("50.00")


def test_material_unloading_tracks_hours_with_zero_payment():
    work = WorkType.objects.get(code="material-unloading")

    assert work.name_de == "Materialentladung auf der Baustelle"
    assert work.name_ru == "Разгрузка материала на объекте"
    assert work.unit == "hour"
    assert work.calculation_rule == "zero"
    assert work.price_mode == "zero"
    assert work.unit_price == Decimal("0.00")
    assert work.is_active is True

    # 1.5 hours, 2 participants -> 3 person-hours in Stundennachweis, 0 € in Leistungsnachweis
    totals = calculate_position(
        work_type=work,
        starts_at=time(11),
        ends_at=time(12, 30),
        participant_count=2,
        quantity=Decimal("1"),
    )
    assert totals.actual_person_hours == Decimal("3.00")
    assert totals.normative_person_hours == Decimal("3.00")
    assert totals.amount == Decimal("0.00")


def test_material_catalog_contains_delivery_and_unloading():
    active_codes = set(WorkType.objects.for_direction("ac").filter(is_active=True).values_list("code", flat=True))
    assert "material-delivery" in active_codes
    assert "material-unloading" in active_codes
