"""Безопасный импорт старых дневных записей во внутренний учёт."""

from dataclasses import dataclass
from datetime import date, time
from uuid import NAMESPACE_URL, uuid5

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from features.projects.models import ProjectGroup
from features.staff.models import Employee

from .models import TeamReport
from .services import review_report, save_report


@dataclass(frozen=True)
class HistoricalTeamReport:
    """Одна нормализованная запись из внешнего исторического источника."""

    source_key: str
    work_date: date
    starts_at: time
    ends_at: time
    direction: str
    participant_names: tuple[str, ...]
    source_location: str


@dataclass(frozen=True)
class HistoricalImportResult:
    """Результат идемпотентной загрузки одной записи."""

    report: TeamReport
    created: bool


def _employees_by_name(names):
    employees = list(Employee.objects.filter(employment_status=Employee.EmploymentStatus.ACTIVE))
    by_name = {}
    for employee in employees:
        by_name.setdefault(str(employee).casefold(), []).append(employee)
    resolved = []
    for name in names:
        matches = by_name.get(name.casefold(), [])
        if len(matches) != 1:
            raise ValidationError(f"Сотрудник «{name}» не найден или имя неоднозначно.")
        resolved.append(matches[0])
    return resolved


def _same_participants(report, employee_ids):
    return set(report.participants.values_list("employee_id", flat=True)) == set(employee_ids)


@transaction.atomic
def import_historical_report(*, actor, group, source):
    """Создать и принять запись один раз, сохранив статусы завершённого проекта."""
    if source.direction not in {"ac", "dc"}:
        raise ValidationError(_("Историческая запись содержит неизвестное направление."))
    if not getattr(group, f"has_{source.direction}"):
        raise ValidationError(f"Проект «{group}» не поддерживает направление {source.direction.upper()}.")

    employees = _employees_by_name(source.participant_names)
    employee_ids = [employee.pk for employee in employees]
    submission_key = uuid5(NAMESPACE_URL, f"dlc-montage:{source.source_key}")
    report = TeamReport.objects.filter(submission_key=submission_key).first()
    if report:
        return HistoricalImportResult(report=report, created=False)

    candidates = TeamReport.objects.filter(
        project_group=group,
        direction=source.direction,
        work_date=source.work_date,
        starts_at=source.starts_at,
        ends_at=source.ends_at,
    ).prefetch_related("participants")
    for candidate in candidates:
        if _same_participants(candidate, employee_ids):
            return HistoricalImportResult(report=candidate, created=False)

    locked_group = ProjectGroup.objects.select_for_update().get(pk=group.pk)
    original_status = locked_group.status
    if original_status != "active":
        locked_group.status = "active"
        locked_group.save(update_fields=["status"])

    report = save_report(
        actor=actor,
        data={
            "submission_key": submission_key,
            "project_group": locked_group,
            "direction": source.direction,
            "work_date": source.work_date,
            "starts_at": source.starts_at,
            "ends_at": source.ends_at,
            "lunch_minutes": 30,
            "work_description": "",
            "note": f"Исторический импорт WhatsApp. Место: {source.source_location}",
        },
        participants=[{"employee": employee, "deduction_minutes": 0} for employee in employees],
        submit=True,
    )
    report = review_report(actor=actor, report_id=report.pk, decision="accept", version=report.version)

    if original_status != "active":
        locked_group.status = original_status
        locked_group.save(update_fields=["status"])
    return HistoricalImportResult(report=report, created=True)
