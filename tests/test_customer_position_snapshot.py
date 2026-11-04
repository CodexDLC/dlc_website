import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from features.customer_portal.customer_position_snapshot import customer_position_digest, customer_position_snapshot
from features.mbg_reports.customer_billing_services import save_customer_package
from features.projects.models import AcObject, ProjectGroup
from features.projects.services import save_site_work_item
from features.work_catalog.models import CustomerWorkPosition, WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def case():
    actor = get_user_model().objects.create_superuser(username="snapshot-owner")
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Snapshot"), name="Haus", status="started")
    mount = save_site_work_item(
        actor=actor,
        site=site,
        work_type=WorkType.objects.get(code="uv-montage"),
        label="private description",
        planned_quantity=1,
    )
    connect = save_site_work_item(
        actor=actor,
        site=site,
        work_type=WorkType.objects.get(code="uv-anschluss"),
        label="private connection",
        planned_quantity=1,
    )
    for item in (mount, connect):
        item.clarified_completed_quantity = 1
        item.completion_clarification_reason = "private reason"
        item.save()
    position = CustomerWorkPosition.objects.get(code="10.010")
    package = save_customer_package(
        actor=actor,
        site=site,
        position=position,
        label="UV private label",
        quantity=1,
        items=[mount, connect],
        note="private note",
    )
    return actor, site, mount, connect, position, package


def test_projection_is_clean_and_explicit(case):
    _, site, _, _, _, _ = case
    rows = customer_position_snapshot(site, include_unperformed=False)
    assert len(rows) == 1
    row = rows[0]
    assert row["key"] == "customer:10.010" and row["quantity"] == "1.00"
    assert row["name_de"] == "Aufbau und Anschluss bauseits gestellter UV-PV"
    assert len(customer_position_snapshot(site, include_unperformed=True)) == 21
    text = json.dumps(rows)
    assert all(word not in text for word in ("private", "price", "amount", "hours", "description", "note"))
    with pytest.raises(TypeError):
        customer_position_snapshot(site)


def test_digest_ignores_price_detects_mapping_and_quantity(case):
    actor, site, mount, _connect, position, package = case
    before = customer_position_digest(site, include_unperformed=False)
    position.unit_price = Decimal("999.00")
    position.save()
    assert customer_position_digest(site, include_unperformed=False) == before
    package.quantity = 2
    package.save()
    assert customer_position_digest(site, include_unperformed=False) != before
    package.quantity = 1
    package.save()
    extra = save_site_work_item(
        actor=actor,
        site=site,
        work_type=WorkType.objects.get(code="uv-anschluss"),
        label="another private",
        planned_quantity=1,
    )
    extra.clarified_completed_quantity = 1
    extra.save()
    save_customer_package(
        actor=actor,
        site=site,
        position=position,
        label=package.label,
        quantity=1,
        items=[mount, extra],
        pk=package.pk,
        note="private",
    )
    assert customer_position_digest(site, include_unperformed=False) != before


def test_missing_revision_rejected(case):
    from datetime import date

    from features.mbg_reports.models import MbgDailyReport

    actor, site, *_ = case
    MbgDailyReport.objects.create(site=site, author=actor, work_date=date(2026, 1, 1), status="accepted")
    with pytest.raises(ValidationError):
        customer_position_snapshot(site, include_unperformed=True)


def test_inactive_catalog_position_remains_visible_at_zero(case):
    _, site, *_ = case
    position = CustomerWorkPosition.objects.get(code="01.0200")
    position.is_active = False
    position.save()
    rows = customer_position_snapshot(site, include_unperformed=True)
    assert len(rows) == 21
    assert next(row for row in rows if row["code"] == "01.0200")["quantity"] == "0.00"
    assert all(row["code"] != "01.0200" for row in customer_position_snapshot(site, include_unperformed=False))
