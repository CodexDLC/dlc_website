"""Транзакции отчётов: проверки, запись, блокировка и история."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.projects.models import ProjectGroup
from features.projects.progress import mark_group_direction_started
from features.staff.models import Employee

from .calculations import duration_minutes
from .models import ReportParticipant, ReportRevision, TeamReport, WorkType
from .policies import can_edit, can_report, directions_for, is_manager


def record_revision(report, actor, action, reason=""):
    """Сохранить независимый снимок после успешного изменения."""
    ReportRevision.objects.create(
        report=report,
        actor=actor,
        action=action,
        reason=reason,
        snapshot={
            "version": report.version,
            "status": report.status,
            "project_group_id": report.project_group_id,
            "project_name": report.project_group.name,
            "author_id": report.author_id,
            "date": str(report.work_date),
            "direction": report.direction,
            "start": str(report.starts_at),
            "end": str(report.ends_at),
            "lunch_minutes": report.lunch_minutes,
            "work": report.work_description,
            "note": report.note,
            "participants": [
                {"employee_id": m.employee_id, "name": str(m.employee), "deduction_minutes": m.deduction_minutes}
                for m in report.participants.select_related("employee")
            ],
        },
    )


@transaction.atomic
def save_report(*, actor, data, participants, submit=False, report_id=None, version=None, reason=""):
    """Сохранить отчёт; все проверки выполняются и при вызове вне HTTP."""
    if not can_report(actor):
        raise PermissionDenied
    # Один ключ формы создаёт только один отчёт даже при повторном HTTP-запросе.
    get_user_model().objects.select_for_update().get(pk=actor.pk)
    if not report_id:
        existing = TeamReport.objects.filter(submission_key=data["submission_key"]).first()
        if existing:
            if existing.author_id != actor.pk:
                raise PermissionDenied
            return existing
    report = None
    if report_id:
        report = TeamReport.objects.select_for_update().get(pk=report_id)
        if not can_edit(actor, report):
            raise PermissionDenied
        if report.version != version:
            raise ValidationError(_("Отчёт уже изменён. Обновите страницу перед сохранением."))
        if is_manager(actor) and not reason.strip():
            raise ValidationError(_("Укажите причину исправления для истории отчёта."))
    if data["direction"] not in dict(directions_for(actor)):
        raise PermissionDenied
    group = ProjectGroup.objects.select_for_update().get(pk=data["project_group"].pk)
    if group.status != "active" or not getattr(group, f"has_{data['direction']}"):
        raise ValidationError(_("Проект недоступен для выбранного направления."))
    base = duration_minutes(data["starts_at"], data["ends_at"])
    if base <= 0 or data["starts_at"].second or data["ends_at"].second:
        raise ValidationError(_("Укажите корректное время начала и окончания с точностью до минут."))
    if data["work_date"] > timezone.localdate():
        raise ValidationError(_("Нельзя отправить отчёт за будущий день."))
    if not 0 <= data["lunch_minutes"] <= base:
        raise ValidationError(_("Обед не может быть длиннее рабочего дня."))
    if not participants:
        raise ValidationError(_("Добавьте хотя бы одного сотрудника."))
    ids = [p["employee"].pk for p in participants]
    if len(ids) != len(set(ids)):
        raise ValidationError(_("Сотрудник указан дважды."))
    # Общая блокировка сотрудников сериализует конкурирующие записи в PostgreSQL.
    locked = list(Employee.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    previous = set(report.participants.values_list("employee_id", flat=True)) if report else set()
    if len(locked) != len(ids) or any(e.employment_status != "active" and e.pk not in previous for e in locked):
        raise ValidationError(_("Выбран недоступный сотрудник."))
    for p in participants:
        if not 0 <= p["deduction_minutes"] < base:
            raise ValidationError(_("Уменьшение должно быть меньше рабочего дня. Не работавшего сотрудника уберите."))
    conflicts = TeamReport.objects.filter(
        work_date=data["work_date"],
        starts_at__lt=data["ends_at"],
        ends_at__gt=data["starts_at"],
        participants__employee_id__in=ids,
    ).exclude(pk=report_id)
    if conflicts.exists():
        raise ValidationError(
            _(
                "У одного из сотрудников уже есть отчёт в этом интервале. "
                "Укажите разные интервалы для разных объектов; уменьшение часов не задаёт время ухода."
            )
        )
    if report is None:
        report = TeamReport(author=actor, submission_key=data["submission_key"])
    for field in (
        "project_group",
        "direction",
        "work_date",
        "starts_at",
        "ends_at",
        "lunch_minutes",
        "work_description",
        "note",
    ):
        setattr(report, field, data[field])
    if report_id:
        report.version += 1
    # Сохранение правки не переводит уже отправленный отчёт обратно в черновик.
    if submit:
        report.status = TeamReport.Status.SUBMITTED
        report.submitted_at = report.submitted_at or timezone.now()
    report.full_clean()
    report.save()
    report.participants.all().delete()
    ReportParticipant.objects.bulk_create(
        [
            ReportParticipant(report=report, employee=p["employee"], deduction_minutes=p["deduction_minutes"])
            for p in participants
        ]
    )
    if report.work_description.strip():
        WorkType.objects.get_or_create(name=report.work_description.strip())
    mark_group_direction_started(group_id=group.pk, direction=report.direction)
    record_revision(report, actor, "submit" if submit else "save", reason)
    return report


@transaction.atomic
def review_report(*, actor, report_id, decision, version, reason=""):
    """Принять или вернуть отчёт; принятие немедленно запрещает правки автора."""
    if not is_manager(actor):
        raise PermissionDenied
    report = TeamReport.objects.select_for_update().get(pk=report_id)
    if version != report.version:
        raise ValidationError(_("Отчёт уже изменён. Обновите страницу."))
    if report.status != TeamReport.Status.SUBMITTED:
        raise ValidationError(_("Проверять можно только отправленный отчёт."))
    if decision not in ("accept", "return"):
        raise ValidationError(_("Неизвестное действие."))
    if decision == "return" and not reason.strip():
        raise ValidationError(_("Напишите, что нужно исправить."))
    report.status = TeamReport.Status.ACCEPTED if decision == "accept" else TeamReport.Status.RETURNED
    report.reviewed_by = actor
    report.reviewed_at = timezone.now()
    report.review_note = reason
    report.version += 1
    report.save()
    record_revision(report, actor, decision, reason)
    return report
