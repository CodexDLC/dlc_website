"""Ввод и проверка клиентского времени; внутренние отчёты не читаются."""

from collections import Counter
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.internal_time.calculations import duration_minutes
from features.internal_time.policies import is_manager
from features.projects.models import AcObject, SiteWorkItem
from features.projects.progress import mark_site_started
from features.staff.models import Employee
from features.work_catalog.models import WorkType

from .calculations import calculate_position
from .models import MbgDailyReport, MbgReportRevision, MbgWorkEntry


def _plain_decimal(value):
    """Вернуть число без незначащих нулей для человекочитаемой позиции."""
    return format(value.normalize(), "f")


def _entry_description(
    *, work, custom_text, route, cable_type, quantity, with_underconstruction, standard_connections, heavy_connections
):
    """Собрать немецкую строку MBG из выбранных структурированных параметров."""
    parts = [custom_text.strip() or work.name_de]
    if route:
        parts.append(route.name_de)
    if cable_type:
        parts.append(cable_type.name_de)
    if with_underconstruction:
        parts.append("mit Unterkonstruktion")
    if standard_connections:
        parts.append(f"{standard_connections} Standardanschlüsse")
    if heavy_connections:
        parts.append(f"{heavy_connections} Schweranschlüsse")
    if quantity != 1:
        parts.append(f"× {_plain_decimal(quantity)}")  # noqa: RUF001
    return " · ".join(parts)


def record_revision(report, actor, action, reason):
    """Снимок сохраняет адрес, номер, имена и немецкие тексты на момент операции."""
    snapshot = {
        "group_id": report.site.group_id,
        "group_name": report.site.group.name,
        "site_id": report.site_id,
        "site_name": report.site.name,
        "address": report.site.address,
        "project_number": report.site.project_number,
        "date": str(report.work_date),
        "status": report.status,
        "workforce": [{"employee_id": employee.pk, "name": str(employee)} for employee in report.workforce.all()],
        "entries": [
            {
                "participants": [
                    {"employee_id": employee.pk, "name": str(employee)} for employee in e.participants.all()
                ],
                "start": str(e.starts_at),
                "end": str(e.ends_at),
                "minutes": duration_minutes(e.starts_at, e.ends_at),
                "custom_description": e.custom_description,
                "description": e.description,
                "work_type_code": e.work_type.code,
                "is_break": e.work_type.is_break,
                "calculation_rule": e.work_type.calculation_rule,
                "unit": e.work_item.unit_snapshot if e.work_item_id else e.work_type.get_unit_display(),
                "work_item_id": e.work_item_id,
                "completed_quantity": str(e.completed_quantity) if e.completed_quantity is not None else None,
                "quantity": str(e.quantity),
                "cable_type": e.cable_type.name_de if e.cable_type else "",
                "route": e.route.name_de if e.route else "",
                "with_underconstruction": e.with_underconstruction,
                "standard_connections": e.standard_connections,
                "heavy_connections": e.heavy_connections,
                "normative_person_hours": str(e.normative_person_hours),
                "actual_person_hours": str(e.actual_person_hours),
                "unit_price": str(e.unit_price),
                "amount": str(e.amount),
                "internal_only": e.internal_only,
            }
            for e in report.entries.select_related("work_type", "work_item", "cable_type", "route").prefetch_related(
                "participants"
            )
        ],
    }
    return MbgReportRevision.objects.create(
        report=report, actor=actor, version=report.version, action=action, reason=reason, snapshot=snapshot
    )


@transaction.atomic
def save_report(
    *,
    actor,
    site,
    work_date,
    workforce,
    entries,
    report_id=None,
    version=None,
    submit=False,
    reason="",
    submission_key=None,
):
    """Атомарно записать состав дня и выполненные позиции MBG."""
    if not is_manager(actor):
        raise PermissionDenied
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    if not site.is_active or not site.group.has_ac or site.group.status != "active":
        raise ValidationError(_("Выберите действующий AC-объект."))
    if work_date > timezone.localdate():
        raise ValidationError(_("Нельзя заполнить будущий день."))
    if not entries or len(entries) > 100:
        raise ValidationError(_("Добавьте от 1 до 100 строк."))
    report = MbgDailyReport.objects.select_for_update().get(pk=report_id) if report_id else None
    if report is None and site.status == "completed":
        raise ValidationError(_("Standort завершён. Сначала верните его в работу."))
    if report:
        if report.version != version:
            raise ValidationError(_("Отчёт уже изменён. Обновите страницу."))
        if report.status == "accepted" and not reason.strip():
            raise ValidationError(_("Укажите причину исправления принятого отчёта."))
    elif submission_key:
        existing = MbgDailyReport.objects.filter(submission_key=submission_key).first()
        if existing:
            return existing
    workforce_ids = {employee.pk for employee in workforce}
    if not workforce_ids:
        raise ValidationError(_("Добавьте сотрудников в состав рабочего дня."))
    people = list(Employee.objects.select_for_update().filter(pk__in=workforce_ids).order_by("pk"))
    if len(people) != len(workforce_ids) or any(e.employment_status != "active" or not e.has_ac_access for e in people):
        raise ValidationError(_("В составе рабочего дня могут быть только действующие сотрудники AC."))
    prepared = []
    for row in entries:
        start, end = row["starts_at"], row["ends_at"]
        if start >= end or start.second or end.second or start.minute % 15 or end.minute % 15:
            raise ValidationError(_("Окончание должно быть позже начала, время вводится шагом 15 минут."))
        participants = list(row["participants"])
        if not participants:
            raise ValidationError(_("Укажите хотя бы одного сотрудника."))
        if {employee.pk for employee in participants} - workforce_ids:
            raise ValidationError(_("Для работы можно выбрать только сотрудников из состава рабочего дня."))
        work = row.get("work_type")
        if not work:
            raise ValidationError(_("Выберите вид работ."))
        work = WorkType.objects.get(pk=work.pk)
        if not work.is_active or not work.supports_direction("ac"):
            raise ValidationError(_("Выберите активный вид работ AC."))
        quantity = row.get("quantity")
        if quantity is None or quantity <= 0:
            raise ValidationError(_("Количество должно быть больше нуля."))
        cable_type = row.get("cable_type")
        route = row.get("route")
        if work.requires_route and not route:
            raise ValidationError(_("Для выбранной работы укажите путь."))
        if work.requires_cable_type and not cable_type:
            raise ValidationError(_("Для прокладки выберите тип кабеля."))
        if not work.requires_cable_type and cable_type:
            raise ValidationError(_("Тип кабеля доступен только для позиции прокладки."))
        work_item = row.get("work_item")
        completed_quantity = row.get("completed_quantity")
        if (work_item is None) != (completed_quantity is None):
            raise ValidationError(_("Позиция Standort и прирост объёма должны быть указаны вместе."))
        if work_item is not None:
            work_item = SiteWorkItem.objects.select_for_update().get(pk=work_item.pk)
            try:
                completed_quantity = Decimal(str(completed_quantity))
            except (InvalidOperation, ValueError) as exc:
                raise ValidationError(_("Укажите корректный прирост объёма.")) from exc
            if not completed_quantity.is_finite() or completed_quantity < 0:
                raise ValidationError(_("Прирост объёма не может быть отрицательным."))
            if work.unit == WorkType.Unit.HOUR or work.calculation_rule in (
                WorkType.CalculationRule.ACTUAL,
                WorkType.CalculationRule.ZERO,
            ):
                raise ValidationError(_("Почасовые работы пока нельзя связывать с физической позицией."))
            if (
                work_item.site_id != site.pk
                or work_item.work_type_id != work.pk
                or work_item.route_id != getattr(route, "pk", None)
                or work_item.cable_type_id != getattr(cable_type, "pk", None)
                or work_item.with_underconstruction != row.get("with_underconstruction", False)
            ):
                raise ValidationError(_("Позиция Standort не соответствует объекту или параметрам работы."))
        totals = calculate_position(
            work_type=work,
            starts_at=start,
            ends_at=end,
            participant_count=len(participants),
            quantity=quantity,
            cable_type=cable_type,
            standard_connections=row.get("standard_connections", 0),
            heavy_connections=row.get("heavy_connections", 0),
            with_underconstruction=row.get("with_underconstruction", False),
        )
        description = _entry_description(
            work=work,
            custom_text=row.get("description", ""),
            route=route,
            cable_type=cable_type,
            quantity=quantity,
            with_underconstruction=row.get("with_underconstruction", False),
            standard_connections=row.get("standard_connections", 0),
            heavy_connections=row.get("heavy_connections", 0),
        )
        prepared.append(
            {
                **row,
                "participants": participants,
                "custom_description": row.get("description", "").strip(),
                "description": description,
                "work_type": work,
                "work_item": work_item,
                "completed_quantity": completed_quantity,
                "quantity": quantity,
                "cable_type": cable_type,
                "route": route,
                "totals": totals,
            }
        )
    for i, row in enumerate(prepared):
        for other in prepared[:i]:
            row_ids = {employee.pk for employee in row["participants"]}
            other_ids = {employee.pk for employee in other["participants"]}
            if row_ids & other_ids and row["starts_at"] < other["ends_at"] and row["ends_at"] > other["starts_at"]:
                raise ValidationError(_("У сотрудника пересекаются строки MBG."))
        if (
            MbgWorkEntry.objects.filter(
                participants__in=row["participants"],
                report__work_date=work_date,
                starts_at__lt=row["ends_at"],
                ends_at__gt=row["starts_at"],
            )
            .exclude(report_id=report_id)
            .distinct()
            .exists()
        ):
            raise ValidationError(_("У сотрудника уже есть работа MBG в это время на другом объекте."))
    if report:
        old_links = Counter(report.entries.exclude(work_item=None).values_list("work_item_id", flat=True))
        new_links = Counter(row["work_item"].pk for row in prepared if row["work_item"])
        if old_links - new_links:
            raise ValidationError(_("Сохраните привязки позиций Standort при редактировании отчёта."))
    if report is None:
        report = MbgDailyReport(author=actor, submission_key=submission_key or uuid4())
    else:
        report.version += 1
    report.site, report.work_date = site, work_date
    if submit and report.status != "accepted":
        report.status = "submitted"
    report.full_clean()
    report.save()
    report.workforce.set(people)
    report.entries.all().delete()
    for position, row in enumerate(prepared):
        entry = MbgWorkEntry(
            report=report,
            position=position,
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            work_type=row["work_type"],
            work_item=row["work_item"],
            completed_quantity=row["completed_quantity"],
            quantity=row["quantity"],
            cable_type=row["cable_type"],
            route=row["route"],
            standard_connections=row.get("standard_connections", 0),
            heavy_connections=row.get("heavy_connections", 0),
            with_underconstruction=row.get("with_underconstruction", False),
            normative_person_hours=row["totals"].normative_person_hours,
            actual_person_hours=row["totals"].actual_person_hours,
            unit_price=(
                row["cable_type"].unit_price_per_ten_meters
                if row["cable_type"] and row["cable_type"].unit_price_per_ten_meters
                else row["work_type"].unit_price
            ),
            amount=row["totals"].amount,
            custom_description=row["custom_description"],
            description=row["description"],
            internal_only=row.get("internal_only", False),
        )
        entry.full_clean()
        entry.save()
        entry.participants.set(row["participants"])
    mark_site_started(site_id=site.pk)
    record_revision(report, actor, "submit" if submit else "save", reason)
    return report


@transaction.atomic
def review_report(*, actor, report_id, version, decision, reason=""):
    """Принятие или возврат создаёт отдельную ревизию."""
    if not is_manager(actor):
        raise PermissionDenied
    report = MbgDailyReport.objects.select_for_update().select_related("site__group").get(pk=report_id)
    if report.version != version or report.status != "submitted":
        raise ValidationError(_("Отчёт уже изменён или не отправлен на проверку."))
    if decision not in ("accept", "return"):
        raise ValidationError(_("Неизвестное действие."))
    if decision == "return" and not reason.strip():
        raise ValidationError(_("Укажите, что исправить."))
    report.status = "accepted" if decision == "accept" else "returned"
    report.review_note = reason
    report.version += 1
    report.save()
    record_revision(report, actor, decision, reason)
    return report
