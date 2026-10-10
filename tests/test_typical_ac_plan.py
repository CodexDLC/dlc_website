"""Reviewable AC plan recipe and atomic first application."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.services import apply_typical_site_plan
from features.projects.typical_plan import TypicalPlanConfig, build_typical_plan

pytestmark = pytest.mark.django_db


@pytest.fixture
def empty_site():
    manager = get_user_model().objects.create_user(username="typical-manager", is_superuser=True)
    site = AcObject.objects.create(group=ProjectGroup.objects.create(name="Typical AC"), name="Haus 1")
    return manager, site


def form_data(**extra):
    data = {
        "inverter_count": "1", "include_nh": "on", "wr_power_cable_code": "power-5x16",
        "data_cable_code": "data", "uv_out_power_cable_code": "power-5x16",
        "nh_out_power_cable_code": "power-5x35", "pe_cable_code": "pe-1x16",
        "control_cable_code": "control-7x1-5", "pe_route_code": "uv-hpas-new",
    }
    data.update(extra)
    return data


def test_default_recipe_has_one_wr_separate_lines_and_nh():
    specs = {spec.key: spec for spec in build_typical_plan(TypicalPlanConfig())}
    assert {"wr-1-mount", "wr-1-connect", "wr-1-power", "wr-1-data"} <= specs.keys()
    assert specs["wr-1-power"].route_code == "wr-uv"
    assert specs["wr-1-data"].cable_type_code == "data"
    assert specs["uv-out-power"].route_code == "uv-nh-new"
    assert "nh-out-power" not in specs
    assert "nh-extension" not in specs
    assert "control-line" not in specs
    assert "tray-wr-uv" not in specs


def test_two_wr_without_nh_and_optional_control_keep_distinct_identities():
    config = TypicalPlanConfig(inverter_count=2, include_nh=False, include_control=True, include_trays=True)
    specs = {spec.key: spec for spec in build_typical_plan(config)}
    assert {"wr-1-power", "wr-2-power", "wr-1-data", "wr-2-data"} <= specs.keys()
    assert specs["wr-1-power"].label != specs["wr-2-power"].label
    assert specs["uv-out-power"].route_code == "uv-hv"
    assert specs["control-line"].route_code == "uv-key-switch"
    assert specs["tray-wr-uv"].route_code == "wr-uv"
    assert "nh-mount" not in specs and "nh-out-power" not in specs


def test_explicit_nh_hv_and_wr_construction_options():
    specs = {spec.key: spec for spec in build_typical_plan(TypicalPlanConfig(
        inverter_count=2, include_nh_hv=True, wr_underconstruction=True, include_trays=True,
    ))}
    assert specs["nh-out-power"].route_code == "nh-new-hv"
    assert specs["tray-nh-hv"].route_code == "nh-new-hv"
    assert specs["wr-1-mount"].with_underconstruction
    assert specs["wr-2-mount"].with_underconstruction


def test_apply_is_atomic_once_and_never_completes_or_rewrites_reports(empty_site):
    manager, site = empty_site
    report = MbgDailyReport.objects.create(
        author=manager, site=site, work_date=timezone.localdate(), status="accepted", version=1,
        submission_key=uuid4(),
    )
    snapshot = {"status": "accepted", "entries": []}
    revision = MbgReportRevision.objects.create(
        report=report, actor=manager, version=1, action="accept", reason="Historie", snapshot=snapshot,
    )
    config = TypicalPlanConfig(inverter_count=2)
    selected = {spec.key: Decimal("1") for spec in build_typical_plan(config)}
    items = apply_typical_site_plan(actor=manager, site=site, config=config, selected=selected)
    assert len(items) == len(selected)
    assert len({item.pk for item in items}) == len(items)
    assert SiteWorkItem.objects.filter(site=site, completion_confirmed_at__isnull=False).count() == 0
    report.refresh_from_db()
    revision.refresh_from_db()
    assert (report.status, report.version, revision.snapshot) == ("accepted", 1, snapshot)
    assert site.mbg_reports.count() == 1
    with pytest.raises(ValidationError):
        apply_typical_site_plan(actor=manager, site=site, config=config, selected=selected)
    assert SiteWorkItem.objects.filter(site=site).count() == len(items)


def test_invalid_selection_and_nonmanager_cannot_apply(empty_site):
    manager, site = empty_site
    config = TypicalPlanConfig()
    with pytest.raises(ValidationError):
        apply_typical_site_plan(actor=manager, site=site, config=config, selected={"bogus": 1})
    with pytest.raises(ValidationError):
        apply_typical_site_plan(actor=manager, site=site, config=config, selected={"uv-mount": 0})
    ordinary = get_user_model().objects.create_user(username="typical-viewer")
    with pytest.raises(PermissionDenied):
        apply_typical_site_plan(actor=ordinary, site=site, config=config, selected={"uv-mount": 1})
    assert SiteWorkItem.objects.filter(site=site).count() == 0


def test_manager_can_preview_and_apply_reviewed_subset(empty_site, client):
    manager, site = empty_site
    client.force_login(manager)
    url = reverse("projects:typical_work_plan", args=[site.group_id, site.pk])
    preview = client.post(url, form_data(step="preview"))
    assert preview.status_code == 200
    assert b"uv-mount" in preview.content
    assert SiteWorkItem.objects.filter(site=site).count() == 0
    apply = client.post(url, form_data(**{
        "step": "apply",
        "include-uv-mount": "on", "quantity-uv-mount": "1",
        "include-wr-1-power": "on", "quantity-wr-1-power": "2",
    }))
    assert apply.status_code == 302, apply.context["form"].errors.as_json()
    assert SiteWorkItem.objects.filter(site=site).count() == 2
    assert SiteWorkItem.objects.get(site=site, label__contains="WR 1").planned_quantity == 2


def test_invalid_quantity_keeps_reviewed_selection_and_value(empty_site, client):
    manager, site = empty_site
    client.force_login(manager)
    url = reverse("projects:typical_work_plan", args=[site.group_id, site.pk])
    response = client.post(url, form_data(**{
        "step": "apply", "include-uv-mount": "on", "quantity-uv-mount": "0",
    }))
    assert response.status_code == 200
    assert "должен быть больше нуля" in response.content.decode()
    assert b'name="quantity-uv-mount"' in response.content
    assert b'value="0"' in response.content
    assert b'name="include-uv-mount" checked' in response.content
    assert SiteWorkItem.objects.filter(site=site).count() == 0
