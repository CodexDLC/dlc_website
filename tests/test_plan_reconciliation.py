"""Исторические групповые строки подтверждают план без изменения принятых документов."""

from copy import deepcopy
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from features.mbg_reports.completion_projection import project_accepted_entries
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision, PlanEntryReconciliation
from features.mbg_reports.plan_reconciliation import reconcile_plan_entry
from features.mbg_reports.work_items import accepted_work_item_progress
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.work_catalog.models import CableType, WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    actor = get_user_model().objects.create_user(username="reconciliation-manager", is_superuser=True)
    group = ProjectGroup.objects.create(name="Plan reconciliation")
    site = AcObject.objects.create(group=group, name="Two inverters")
    work = WorkType.objects.create(
        code="grouped-data-cable", name_de="Datenkabel", unit="piece", calculation_rule="fixed"
    )
    cable = CableType.objects.create(
        code="reconcile-data",
        name_de="Cat7",
        category="data",
        normative_hours_per_ten_meters=1,
    )
    items = [
        SiteWorkItem.objects.create(
            site=site,
            work_type=work,
            cable_type=cable,
            label=f"WR {index} Datenkabel",
            planned_quantity=1,
            unit_snapshot="Stk.",
        )
        for index in (1, 2)
    ]
    source = {
        "description": "Datenkabel WR 1 und 2 → UV",
        "work_type_code": work.code,
        "unit": "Stk.",
        "calculation_rule": "fixed",
        "cable_type": cable.name_de,
        "actual_person_hours": "2.00",
        "quantity": "1.00",
        "completed_quantity": "1.00",
        "work_item_id": items[0].pk,
        "internal_only": False,
    }
    report = MbgDailyReport.objects.create(site=site, author=actor, work_date=timezone.localdate(), status="accepted")
    revision = MbgReportRevision.objects.create(
        report=report,
        actor=actor,
        version=report.version,
        action="accept",
        snapshot={"status": "accepted", "entries": [source]},
    )
    return actor, report, revision, items


def allocate(data, *, reason="Both cables explicitly confirmed by original note", **kwargs):
    actor, _report, revision, items = data
    allocations = [{"work_item_id": item.pk, "completed_quantity": "1", "actual_person_hours": "1"} for item in items]
    arguments = {
        "actor": actor,
        "revision_id": revision.pk,
        "entry_index": 0,
        "allocations": allocations,
        "reason": reason,
    }
    arguments.update(kwargs)
    return reconcile_plan_entry(**arguments)


def test_explicit_grouped_reconciliation_preserves_report_and_other_projections(data):
    _actor, report, revision, items = data
    before = deepcopy(revision.snapshot)
    accepted = [(report.pk, report.version, report.work_date, before)]
    customer_before = project_accepted_entries(accepted)
    mapping = allocate(data)
    assert allocate(data).pk == mapping.pk
    mapping.refresh_from_db()
    assert len(mapping.history) == 1
    progress = accepted_work_item_progress(site_id=report.site_id)
    assert {row.work_item_id: row.completed_quantity for row in progress.items} == {
        item.pk: Decimal("1") for item in items
    }
    assert sum(row.actual_person_hours for row in progress.items) == Decimal("2")
    revision.refresh_from_db()
    report.refresh_from_db()
    assert revision.snapshot == before
    assert report.status == "accepted" and report.version == 1
    assert (
        project_accepted_entries([(report.pk, report.version, report.work_date, revision.snapshot)]) == customer_before
    )


def test_replacing_mapping_keeps_audit_without_double_counting(data):
    _actor, report, _revision, items = data
    allocate(data)
    mapping = allocate(
        data,
        reason="Confirmed only second physical cable",
        allocations=[
            {
                "work_item_id": items[1].pk,
                "completed_quantity": "1",
                "actual_person_hours": "2",
            }
        ],
    )
    assert len(mapping.history) == 2
    assert PlanEntryReconciliation.objects.count() == 1
    progress = accepted_work_item_progress(site_id=report.site_id)
    assert [(row.work_item_id, row.actual_person_hours) for row in progress.items] == [(items[1].pk, Decimal("2"))]


def test_manager_authorization_and_reason_required(data):
    outsider = get_user_model().objects.create_user(username="reconciliation-outsider")
    with pytest.raises(PermissionDenied):
        allocate(data, actor=outsider)
    with pytest.raises(ValidationError):
        allocate(data, reason="  ")
    assert not PlanEntryReconciliation.objects.exists()


@pytest.mark.parametrize("index", [-1, 1, True, "0"])
def test_invalid_snapshot_index_rejected(data, index):
    with pytest.raises(ValidationError):
        allocate(data, entry_index=index)


@pytest.mark.parametrize(
    "change",
    [
        {"is_break": True},
        {"calculation_rule": "actual"},
        {"calculation_rule": "zero"},
        {"unit": "Std."},
    ],
)
def test_nonphysical_sources_cannot_complete_plan(data, change):
    revision = data[2]
    revision.snapshot["entries"][0].update(change)
    revision.save(update_fields=["snapshot"])
    with pytest.raises(ValidationError):
        allocate(data)


@pytest.mark.parametrize("hours", ["3", "0", "-1", "NaN", "Infinity", "0.001"])
def test_allocated_hours_must_preserve_source_total(data, hours):
    with pytest.raises(ValidationError):
        allocate(
            data,
            allocations=[
                {
                    "work_item_id": data[3][0].pk,
                    "completed_quantity": "1",
                    "actual_person_hours": hours,
                }
            ],
        )


@pytest.mark.parametrize("attribute", ["site", "work_type", "unit", "cable", "excluded"])
def test_wrong_site_or_work_identity_rejected(data, attribute):
    item = data[3][1]
    if attribute == "site":
        item.site = AcObject.objects.create(group=data[1].site.group, name="Other site")
    elif attribute == "work_type":
        item.work_type = WorkType.objects.get(code="cable-tray")
    elif attribute == "unit":
        item.unit_snapshot = "bis 10 m"
    elif attribute == "cable":
        item.cable_type = None
    else:
        item.is_required = False
    item.save()
    with pytest.raises(ValidationError):
        allocate(data)


def test_internal_source_stays_excluded_from_customer_filter(data):
    revision = data[2]
    revision.snapshot["entries"][0]["internal_only"] = True
    revision.save(update_fields=["snapshot"])
    allocate(data)
    assert len(accepted_work_item_progress(site_id=data[1].site_id).items) == 2
    assert accepted_work_item_progress(site_id=data[1].site_id, include_internal=False).items == ()


@pytest.mark.parametrize("change", ["revoked", "new_version", "missing_snapshot"])
def test_obsolete_or_revoked_report_does_not_use_reconciliation(data, change):
    allocate(data)
    report = data[1]
    if change == "revoked":
        report.status = "returned"
    else:
        report.version += 1
    report.save()
    if change == "new_version":
        MbgReportRevision.objects.create(
            report=report,
            actor=data[0],
            version=report.version,
            action="accept",
            snapshot={"status": "accepted", "entries": []},
        )
    assert accepted_work_item_progress(site_id=report.site_id).items == ()
    with pytest.raises(ValidationError):
        allocate(data)


def test_removed_plan_mapping_falls_back_to_original_evidence(data):
    allocate(data)
    SiteWorkItem.objects.filter(pk=data[3][1].pk).update(is_required=False)
    progress = accepted_work_item_progress(site_id=data[1].site_id)
    assert [row.work_item_id for row in progress.items] == [data[3][0].pk]


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "1000000", "0.001"])
def test_invalid_physical_quantities_rejected(data, quantity):
    with pytest.raises(ValidationError):
        allocate(
            data,
            allocations=[
                {
                    "work_item_id": data[3][0].pk,
                    "completed_quantity": quantity,
                    "actual_person_hours": "2",
                }
            ],
        )


def test_duplicate_targets_are_rejected(data):
    row = {"work_item_id": data[3][0].pk, "completed_quantity": "1", "actual_person_hours": "1"}
    with pytest.raises(ValidationError):
        allocate(data, allocations=[row, row])


def test_unaccepted_snapshot_cannot_supply_evidence(data):
    revision = data[2]
    revision.snapshot["status"] = "submitted"
    revision.save(update_fields=["snapshot"])
    with pytest.raises(ValidationError):
        allocate(data)
    assert accepted_work_item_progress(site_id=data[1].site_id).items == ()


def test_zero_source_hours_need_no_invented_positive_allocation(data):
    revision = data[2]
    revision.snapshot["entries"][0]["actual_person_hours"] = "0"
    revision.save(update_fields=["snapshot"])
    allocate(
        data,
        allocations=[
            {
                "work_item_id": item.pk,
                "completed_quantity": "1",
                "actual_person_hours": "0",
            }
            for item in data[3]
        ],
    )
    progress = accepted_work_item_progress(site_id=data[1].site_id)
    assert len(progress.items) == 2
    assert all(row.actual_person_hours == 0 for row in progress.items)
