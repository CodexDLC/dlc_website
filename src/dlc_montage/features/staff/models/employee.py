from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    """A worker, which may exist before receiving a cabinet account."""

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        ABSENT = "absent", _("Absent")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee"
    )
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    phone = models.CharField(_("phone"), max_length=50, blank=True)
    email = models.EmailField(_("email"), blank=True)
    hourly_rate_eur = models.DecimalField(
        _("Почасовая ставка brutto, €"),
        max_digits=7,
        decimal_places=2,
        default=Decimal("13.90"),
    )
    employment_status = models.CharField(
        max_length=16, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )
    has_ac_access = models.BooleanField(_("AC access"), default=False)
    has_dc_access = models.BooleanField(_("DC access"), default=False)
    is_foreman = models.BooleanField(_("is foreman"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
