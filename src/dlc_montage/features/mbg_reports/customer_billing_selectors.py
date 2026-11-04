"""Чтение расчётного списка заказчика без изменения первичных отчётов."""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import F, Prefetch

from features.projects.models import SiteWorkItem
from features.work_catalog.customer_selectors import customer_positions

from .accepted_revisions import load_accepted_current_revisions
from .completion_projection import project_accepted_entries
from .customer_billing_projection import PackageProgress, RequirementProgress
from .models import (
    CustomerWorkPackage,
    CustomerWorkRequirement,
    MbgDailyReport,
    MbgReportRevision,
    PlanEntryReconciliation,
)
from .plan_reconciliation import reconciled_plan_snapshot
from .selectors import GroupPositionRow

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CustomerBillingSummary:
    rows: tuple[GroupPositionRow, ...]
    packages: tuple[PackageProgress, ...]
    unmapped_rows: tuple[GroupPositionRow, ...]
    unassigned_items: tuple[SiteWorkItem, ...]
    excluded_reports: tuple[int, ...]
    known_subtotal: Decimal
    amount: Decimal | None


def _physical_rows(site, items):
    reports = list(MbgDailyReport.objects.filter(site=site, status="accepted").order_by("work_date", "pk"))
    batch = load_accepted_current_revisions(reports)
    revisions = {
        (r.report_id, r.version): r
        for r in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
    }
    mappings = {
        (m.revision_id, m.entry_index): m
        for m in PlanEntryReconciliation.objects.filter(revision__in=revisions.values())
    }
    snapshots = []
    for report, snapshot in batch.items:
        revision = revisions[(report.pk, report.version)]
        snapshot = reconciled_plan_snapshot(revision=revision, mappings=mappings, items=items) if mappings else snapshot
        snapshots.append((report.pk, report.version, report.work_date, snapshot))
    return project_accepted_entries(snapshots, include_internal=False), batch.excluded_report_ids


def customer_billing_summary(site):
    """Собрать исходные номера заказчика, готовые пакеты и непокрытые работы."""
    items = {
        item.pk: item
        for item in SiteWorkItem.objects.filter(site=site).select_related("work_type", "route", "cable_type")
    }
    physical, excluded = _physical_rows(site, items)
    by_item = {r.work_item_id: r for r in physical if r.kind == "linked"}
    packages = list(
        CustomerWorkPackage.objects.filter(site=site, is_active=True)
        .select_related("position")
        .prefetch_related(
            Prefetch("requirements", queryset=CustomerWorkRequirement.objects.select_related("work_item"))
        )
    )
    progress = []
    used = set()
    sources_by_code = {}
    quantities = {}
    states = {}
    for package in packages:
        requirements = []
        sources = []
        for requirement in package.requirements.all():
            item = items.get(requirement.work_item_id)
            if item is None:
                continue
            physical_row = by_item.get(item.pk)
            completed = physical_row.quantity if physical_row else ZERO
            if item.clarified_completed_quantity and item.clarified_completed_quantity > completed:
                completed = item.clarified_completed_quantity
                sources.append(
                    {
                        "kind": "plan_clarification",
                        "work_item_id": item.pk,
                        "completed_quantity": str(completed),
                        "reason": item.completion_clarification_reason,
                        "confirmed_at": item.completion_confirmed_at.isoformat()
                        if item.completion_confirmed_at
                        else "",
                    }
                )
            requirements.append(
                RequirementProgress(item.pk, item.label, requirement.required_quantity, completed, item.is_required)
            )
            if physical_row:
                sources.extend(physical_row.sources)
            used.add(item.pk)
        if package.manual_confirmed:
            sources.append(
                {
                    "kind": "manual_customer_quantity",
                    "package_id": package.pk,
                    "quantity": str(package.quantity),
                    "reason": package.note,
                }
            )
        state = PackageProgress(package, tuple(requirements), tuple(sources))
        progress.append(state)
        code = package.position.code
        quantities[code] = quantities.get(code, ZERO) + state.quantity
        sources_by_code.setdefault(code, []).extend(sources)
        states.setdefault(code, []).append(state.state)

    unmapped = []
    free_rows = []
    catalog = list(customer_positions())
    catalog_by_code = {p.code: p for p in catalog}
    for physical_row in physical:
        if physical_row.work_item_id in used:
            continue
        source = physical_row.sources[0]
        code = source["work_type_code"]
        if code == "sonstige" and physical_row.kind == "hourly" and "01.0090" in catalog_by_code:
            confirmed = tuple(
                s
                for s in physical_row.sources
                if s.get("include_in_acceptance") is True and s["calculation_rule"] == "actual"
            )
            if confirmed:
                quantities["01.0090"] = quantities.get("01.0090", ZERO) + sum(
                    (Decimal(s["actual_person_hours"]) for s in confirmed), ZERO
                )
                sources_by_code.setdefault("01.0090", []).extend(confirmed)
            # Unchecked other work explains time; it is neither extra revenue nor an unresolved invoice item.
            continue
        target = "01.0110" if code == "material-delivery" and physical_row.kind == "flat" else None
        if target and target in catalog_by_code and physical_row.quantity is not None:
            # Daily logistics rows retain all time but represent one delivery flat per site.
            quantities[target] = max(quantities.get(target, ZERO), Decimal("1"))
            sources_by_code.setdefault(target, []).extend(physical_row.sources)
            continue
        if physical_row.kind == "photo_package" or all(s["calculation_rule"] == "zero" for s in physical_row.sources):
            free_rows.append(
                GroupPositionRow(
                    code=code,
                    name=physical_row.name,
                    unit=physical_row.unit,
                    quantity=physical_row.quantity,
                    normative_person_hours=None,
                    actual_person_hours=physical_row.actual_person_hours,
                    unit_price=ZERO,
                    amount=ZERO,
                    price_state="free",
                    work_item_id=physical_row.work_item_id,
                    sources=physical_row.sources,
                )
            )
            continue
        unmapped.append(
            GroupPositionRow(
                code=f"unmapped:{code}:{physical_row.work_item_id or len(unmapped)}",
                name=physical_row.name,
                unit=physical_row.unit,
                quantity=physical_row.quantity,
                normative_person_hours=None,
                actual_person_hours=physical_row.actual_person_hours,
                unit_price=None,
                amount=None,
                price_state="unmapped",
                work_item_id=physical_row.work_item_id,
                sources=physical_row.sources,
            )
        )

    rows = []
    # An inactive catalogue record must not silently erase its existing packages.
    for package in packages:
        if package.position.code not in catalog_by_code:
            catalog.append(package.position)
            catalog_by_code[package.position.code] = package.position
    for position in catalog:
        quantity = quantities.get(position.code, ZERO)
        sources = tuple(sources_by_code.get(position.code, ()))
        amount = (quantity * position.unit_price).quantize(Decimal("0.01"))
        name = position.name_de
        if position.code == "01.0090" and sources:
            descriptions = sorted({s["description"] for s in sources if s.get("description")})
            if descriptions:
                name += " · " + "; ".join(descriptions)
        rows.append(
            GroupPositionRow(
                code=position.code,
                name=name,
                unit=position.get_unit_display(),
                quantity=quantity,
                normative_person_hours=None,
                actual_person_hours=ZERO,
                unit_price=position.unit_price,
                amount=amount,
                price_state="customer_agreed",
                work_item_id=None,
                sources=sources,
            )
        )
    rows.extend(free_rows)
    known = sum((r.amount for r in rows), ZERO)
    pending = any(p.state != "completed" for p in progress)
    unassigned = tuple(item for item in items.values() if item.is_required and item.pk not in used)
    return CustomerBillingSummary(
        tuple(rows),
        tuple(progress),
        tuple(unmapped),
        unassigned,
        tuple(excluded),
        known,
        None if excluded or unmapped or pending else known,
    )
