"""Demo data never references operational projects, employees or reports."""

from typing import ClassVar

from django.conf import settings
from django.db import models


class DemoWorkspace(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="demo_workspace")
    created_at = models.DateTimeField(auto_now_add=True)


class DemoWorkType(models.Model):
    workspace = models.ForeignKey(DemoWorkspace, on_delete=models.CASCADE, related_name="work_types")
    name_de = models.CharField("Tätigkeit", max_length=255)
    unit = models.CharField(
        "Einheit", max_length=16, choices=[("hour", "Std."), ("piece", "Stk."), ("meter", "m")], default="hour"
    )
    is_break = models.BooleanField("Pause (keine Arbeitsstunden)", default=False)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        ordering: ClassVar = ["name_de", "pk"]

    def __str__(self):
        return self.name_de


class DemoEmployee(models.Model):
    workspace = models.ForeignKey(DemoWorkspace, on_delete=models.CASCADE, related_name="employees")
    name = models.CharField("Name", max_length=120)

    class Meta:
        ordering: ClassVar = ["name", "pk"]

    def __str__(self):
        return self.name


class DemoDailyReport(models.Model):
    workspace = models.ForeignKey(DemoWorkspace, on_delete=models.CASCADE, related_name="reports")
    date = models.DateField("Datum")
    site_name = models.CharField("Standort", max_length=120)
    address = models.CharField("Adresse", max_length=255, blank=True)
    project_number = models.CharField("P/Nr", max_length=60, blank=True)
    workforce = models.ManyToManyField(DemoEmployee, related_name="reports")
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["-date", "-pk"]


class DemoWorkEntry(models.Model):
    report = models.ForeignKey(DemoDailyReport, on_delete=models.CASCADE, related_name="entries")
    work_type = models.ForeignKey(DemoWorkType, on_delete=models.PROTECT, related_name="entries")
    participants = models.ManyToManyField(DemoEmployee, related_name="entries")
    starts_at = models.TimeField("Beginn")
    ends_at = models.TimeField("Ende")
    quantity = models.DecimalField("Menge", max_digits=9, decimal_places=2, default=1)
    description = models.CharField("Beschreibung", max_length=1000, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering: ClassVar = ["position", "pk"]
