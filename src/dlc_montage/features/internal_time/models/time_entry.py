"""Дневной отчёт команды и независимая история его изменений."""

from typing import ClassVar
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _


class WorkType(models.Model):
    """Сохранённая текстовая метка выполненных работ."""

    name = models.CharField(_("Вид работы"), max_length=180, unique=True)

    class Meta:
        ordering: ClassVar = ["name"]
        verbose_name = _("вид работы")
        verbose_name_plural = "Виды работ"

    def __str__(self):
        return self.name


class TeamReport(models.Model):
    """Один проект, одно направление и общий интервал команды за день."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        SUBMITTED = "submitted", _("Отправлен")
        ACCEPTED = "accepted", _("Принят")
        RETURNED = "returned", _("На исправлении")

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="team_reports")
    submission_key = models.UUIDField(default=uuid4, unique=True, editable=False)
    project_group = models.ForeignKey("projects.ProjectGroup", on_delete=models.PROTECT, related_name="team_reports")
    direction = models.CharField(max_length=2, choices=[("ac", "AC"), ("dc", "DC")])
    work_date = models.DateField()
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    lunch_minutes = models.PositiveSmallIntegerField(default=30)
    work_description = models.CharField(max_length=180, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_team_reports"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["-work_date", "-pk"]
        permissions: ClassVar = [
            ("manage_reports", _("Проверять и исправлять все внутренние отчёты")),
            ("submit_reports", _("Заполнять внутренние отчёты")),
            ("access_ac", _("Заполнять отчёты AC")),
            ("access_dc", _("Заполнять отчёты DC")),
        ]
        constraints: ClassVar = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="team_report_positive_interval")
        ]
        verbose_name = _("отчёт команды")
        verbose_name_plural = "Отчёты команд"

    def __str__(self):
        return f"{self.work_date} · {self.project_group} · {self.direction.upper()}"


class ReportParticipant(models.Model):
    """Состав конкретного отчёта не меняется при изменении сохранённой команды."""

    report = models.ForeignKey(TeamReport, on_delete=models.CASCADE, related_name="participants")
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="report_participations")
    deduction_minutes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(fields=["report", "employee"], name="unique_report_participant")
        ]


class ReportRevision(models.Model):
    """Снимок отчёта после каждого сохранения или решения проверяющего."""

    report = models.ForeignKey(TeamReport, on_delete=models.CASCADE, related_name="revisions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-pk"]
