"""Устойчивые плановые позиции отдельного Standort."""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteWorkItem(models.Model):
    """Физическая работа с неизменной идентичностью внутри Standort."""

    site = models.ForeignKey("projects.AcObject", on_delete=models.PROTECT, related_name="work_items")
    work_type = models.ForeignKey("work_catalog.WorkType", on_delete=models.PROTECT)
    label = models.CharField(max_length=255)
    planned_quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit_snapshot = models.CharField(max_length=32)
    route = models.ForeignKey("work_catalog.CableRoute", on_delete=models.PROTECT, null=True, blank=True)
    cable_type = models.ForeignKey("work_catalog.CableType", on_delete=models.PROTECT, null=True, blank=True)
    with_underconstruction = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)
    completion_confirmed_at = models.DateTimeField(null=True, blank=True)
    clarified_completed_quantity = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    completion_clarification_reason = models.TextField(blank=True, default="")
    completion_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="confirmed_site_work_items",
    )
    not_required_reason = models.TextField(blank=True, default="")
    not_required_at = models.DateTimeField(null=True, blank=True)
    not_required_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="excluded_site_work_items",
    )

    class Meta:
        ordering: ClassVar = ["site_id", "pk"]
        constraints: ClassVar = [
            models.CheckConstraint(
                condition=models.Q(clarified_completed_quantity__isnull=True)
                | models.Q(clarified_completed_quantity__gt=Decimal("0")),
                name="site_work_item_positive_clarification",
            ),
            models.CheckConstraint(
                condition=models.Q(planned_quantity__gt=Decimal("0")), name="site_work_item_positive_plan"
            )
        ]

    def __str__(self):
        return self.label

    def delete(self, *args, **kwargs):
        raise ValidationError(_("Позиция Standort сохраняется в истории; удаление запрещено."))
