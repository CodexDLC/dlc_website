"""Расшифровка исторических групповых строк только для выполнения плана."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from features.internal_time.policies import is_manager
from features.projects.models import SiteWorkItem

from .models import MbgDailyReport, MbgReportRevision, PlanEntryReconciliation


def _number(value, *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("Некорректное количество или часы.") from exc
    if not result.is_finite() or result < 0 or result > Decimal("999999.99") or (positive and result == 0):
        raise ValidationError("Количество должно быть положительным, часы — неотрицательными.")
    if result != result.quantize(Decimal("0.01")):
        raise ValidationError("Допускается не более двух знаков после запятой.")
    return result


def _physical_entry(snapshot, entry_index):
    entries = snapshot.get("entries", [])
    if type(entry_index) is not int or not 0 <= entry_index < len(entries):
        raise ValidationError("Строка принятого снимка не найдена.")
    entry = entries[entry_index]
    if (
        entry.get("is_break")
        or entry.get("work_type_code") == "mittagspause"
        or entry.get("calculation_rule") in {"actual", "zero"}
        or entry.get("unit") in {"Std.", "hour"}
    ):
        raise ValidationError("Паузы и почасовые строки не подтверждают физический объём плана.")
    return entry


def _validate_allocations(*, source, allocations, items, site_id):
    if not isinstance(allocations, list) or not allocations:
        raise ValidationError("Укажите подтверждённые позиции и распределение часов.")
    normalized = []
    seen = set()
    for row in allocations:
        if not isinstance(row, dict):
            raise ValidationError("Некорректная расшифровка позиции.")
        item_id = row.get("work_item_id")
        if type(item_id) is not int:
            raise ValidationError("Укажите идентификатор физической позиции.")
        item = items.get(item_id)
        if item is None or item.site_id != site_id or item_id in seen or not item.is_required:
            raise ValidationError("Выберите разные действующие позиции этого Standort.")
        seen.add(item_id)
        if (
            item.work_type.code != source.get("work_type_code")
            or item.unit_snapshot != source.get("unit")
            or (item.cable_type.name_de if item.cable_type else "") != source.get("cable_type", "")
            or item.with_underconstruction != bool(source.get("with_underconstruction", False))
        ):
            raise ValidationError("Вид работы, единица, кабель и конструкция должны совпадать с принятой строкой.")
        normalized.append(
            {
                "work_item_id": item_id,
                "completed_quantity": str(_number(row.get("completed_quantity"), positive=True)),
                "actual_person_hours": str(_number(row.get("actual_person_hours"))),
            }
        )
    if sum((Decimal(row["actual_person_hours"]) for row in normalized), Decimal("0")) != _number(
        source.get("actual_person_hours", "0")
    ):
        raise ValidationError("Распределённые часы должны точно сохранять часы исходной строки.")
    return sorted(normalized, key=lambda row: row["work_item_id"])


@transaction.atomic
def reconcile_plan_entry(*, actor, revision_id, entry_index, allocations, reason):
    """Сохранить явную расшифровку, не меняя снимок, деньги и приёмку заказчика."""
    if not is_manager(actor):
        raise PermissionDenied
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError("Укажите источник подтверждения и причину расшифровки.")
    revision_hint = MbgReportRevision.objects.get(pk=revision_id)
    report = MbgDailyReport.objects.select_for_update().get(pk=revision_hint.report_id)
    revision = MbgReportRevision.objects.select_for_update().get(pk=revision_id)
    if (
        report.status != "accepted"
        or report.version != revision.version
        or revision.snapshot.get("status") != "accepted"
    ):
        raise ValidationError("Расшифровка допустима только для текущего принятого снимка.")
    source = _physical_entry(revision.snapshot, entry_index)
    items = {
        item.pk: item
        for item in SiteWorkItem.objects.select_for_update(of=("self",))
        .select_related("work_type", "cable_type")
        .filter(site_id=report.site_id)
    }
    normalized = _validate_allocations(source=source, allocations=allocations, items=items, site_id=report.site_id)
    mapping, _created = PlanEntryReconciliation.objects.get_or_create(
        revision=revision,
        entry_index=entry_index,
        defaults={"actor": actor, "reason": reason.strip()},
    )
    if mapping.allocations == normalized and mapping.reason == reason.strip():
        return mapping
    mapping.allocations = normalized
    mapping.actor = actor
    mapping.reason = reason.strip()
    mapping.history = [
        *mapping.history,
        {
            "actor_id": actor.pk,
            "reason": mapping.reason,
            "allocations": normalized,
            "at": timezone.now().isoformat(),
        },
    ]
    mapping.save()
    return mapping


def reconciled_plan_snapshot(*, revision, mappings, items):
    """Вернуть копию снимка для плана; другие проекции читают исходный документ."""
    snapshot = deepcopy(revision.snapshot)
    entries = []
    for index, source in enumerate(snapshot.get("entries", [])):
        mapping = mappings.get((revision.pk, index))
        if mapping is None:
            entries.append(source)
            continue
        try:
            _physical_entry(snapshot, index)
            allocations = _validate_allocations(
                source=source,
                allocations=mapping.allocations,
                items=items,
                site_id=revision.report.site_id,
            )
        except ValidationError:
            # Invalidated positions never gain completion from obsolete mappings.
            entries.append(source)
            continue
        for allocation in allocations:
            item = items[allocation["work_item_id"]]
            entry = deepcopy(source)
            entry.update(allocation)
            entry["description"] = item.label
            entry["route"] = item.route.name_de if item.route else ""
            entries.append(entry)
    snapshot["entries"] = entries
    return snapshot
