"""Независимые от внутренних часов данные MBG."""

from decimal import Decimal
from typing import ClassVar
from uuid import uuid4

from core.private_storage import private_storage
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

CURRENT_WEEKLY_EXPORT_TEMPLATE = "ac-weekly-4"
CURRENT_FINAL_HOURLY_EXPORT_TEMPLATE = "ac-final-hours-1"
CURRENT_WORK_COMPLETION_EXPORT_TEMPLATE = "ac-work-completion-3"


class MbgDailyReport(models.Model):
    site = models.ForeignKey("projects.AcObject", on_delete=models.PROTECT, related_name="mbg_reports")
    work_date = models.DateField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    workforce = models.ManyToManyField("staff.Employee", related_name="mbg_daily_reports")
    submission_key = models.UUIDField(default=uuid4, unique=True)
    status = models.CharField(
        max_length=16,
        default="draft",
        choices=[
            ("draft", _("Черновик")),
            ("submitted", _("Отправлен")),
            ("accepted", _("Принят")),
            ("returned", _("Возвращён")),
        ],
    )
    version = models.PositiveIntegerField(default=1)
    review_note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["-work_date", "-pk"]
        constraints: ClassVar = [models.UniqueConstraint(fields=["site", "work_date"], name="unique_mbg_site_day")]


class MbgWorkEntry(models.Model):
    report = models.ForeignKey(MbgDailyReport, on_delete=models.CASCADE, related_name="entries")
    participants = models.ManyToManyField("staff.Employee", related_name="mbg_work_entries")
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    work_type = models.ForeignKey("work_catalog.WorkType", on_delete=models.PROTECT, null=True, blank=True)
    work_item = models.ForeignKey(
        "projects.SiteWorkItem", on_delete=models.PROTECT, null=True, blank=True, related_name="mbg_entries"
    )
    completed_quantity = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1"))
    cable_type = models.ForeignKey(
        "work_catalog.CableType", on_delete=models.PROTECT, null=True, blank=True, related_name="mbg_entries"
    )
    route = models.ForeignKey(
        "work_catalog.CableRoute", on_delete=models.PROTECT, null=True, blank=True, related_name="mbg_entries"
    )
    standard_connections = models.PositiveSmallIntegerField(default=0)
    heavy_connections = models.PositiveSmallIntegerField(default=0)
    with_underconstruction = models.BooleanField(default=False)
    normative_person_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    actual_person_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custom_description = models.CharField(max_length=500, blank=True, default="")
    description = models.CharField(max_length=500)
    internal_only = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering: ClassVar = ["position", "pk"]
        constraints: ClassVar = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")), name="mbg_entry_positive_interval"
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="mbg_entry_positive_quantity"),
            models.CheckConstraint(
                condition=models.Q(completed_quantity__gte=0) | models.Q(completed_quantity__isnull=True),
                name="mbg_entry_nonnegative_completed_quantity",
            ),
            models.CheckConstraint(
                condition=(models.Q(work_item__isnull=True) & models.Q(completed_quantity__isnull=True))
                | (models.Q(work_item__isnull=False) & models.Q(completed_quantity__isnull=False)),
                name="mbg_entry_work_item_delta_together",
            ),
        ]


class MbgReportRevision(models.Model):
    report = models.ForeignKey(MbgDailyReport, on_delete=models.PROTECT, related_name="revisions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    action = models.CharField(max_length=64)
    reason = models.TextField(blank=True)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-pk"]
        constraints: ClassVar = [models.UniqueConstraint(fields=["report", "version"], name="unique_mbg_revision")]


def export_path(instance, filename):
    return f"reports/mbg/weekly/{instance.year}/KW{instance.week:02}/{uuid4().hex}.xlsx"


class WeeklyExport(models.Model):
    year = models.PositiveIntegerField()
    week = models.PositiveSmallIntegerField()
    fingerprint = models.CharField(max_length=64, unique=True)
    template_version = models.CharField(max_length=20, default="prototype-1")
    snapshot = models.JSONField()
    file = models.FileField(upload_to=export_path, storage=private_storage)
    filename = models.CharField(max_length=250)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-pk"]


def final_hourly_export_path(instance, filename):
    return f"projects/{instance.group_id}/reports/mbg/stundennachweis/final/{uuid4().hex}.xlsx"


class FinalHourlyExport(models.Model):
    """Неизменяемый почасовой Stundennachweis завершённой Anlage за весь период."""

    group = models.ForeignKey(
        "projects.ProjectGroup",
        on_delete=models.PROTECT,
        related_name="final_hourly_exports",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    fingerprint = models.CharField(max_length=64, unique=True)
    template_version = models.CharField(max_length=24, default=CURRENT_FINAL_HOURLY_EXPORT_TEMPLATE)
    snapshot = models.JSONField()
    file = models.FileField(upload_to=final_hourly_export_path, storage=private_storage)
    filename = models.CharField(max_length=250)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-pk"]


def performance_export_path(instance, filename):
    folder = f"projects/{instance.group_id}" if instance.group_id else "reports/mbg/performance"
    document_folder = (
        "leistungsnachweis_ohne_preise" if instance.document_type == "work_completion" else "leistungsnachweis"
    )
    return f"{folder}/reports/mbg/{document_folder}/{uuid4().hex}.xlsx"


class PerformanceExport(models.Model):
    """Неизменяемый Leistungsnachweis или Zwischennachweis Standorte одной или нескольких Anlagen."""

    group = models.ForeignKey(
        "projects.ProjectGroup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="performance_exports",
    )
    document_type = models.CharField(
        max_length=32,
        choices=[
            ("priced_performance", "Leistungsnachweis mit Preisen"),
            ("work_completion", "Leistungsnachweis ohne Preise"),
        ],
        default="priced_performance",
    )
    fingerprint = models.CharField(max_length=64, unique=True)
    template_version = models.CharField(max_length=20, default="prototype-1")
    snapshot = models.JSONField()
    file = models.FileField(upload_to=performance_export_path, storage=private_storage)
    filename = models.CharField(max_length=250)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-pk"]
