from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Crew(models.Model):
    owner = models.ForeignKey("staff.Employee", on_delete=models.CASCADE, related_name="owned_crews")
    name = models.CharField(_("name"), max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_crew_name_per_owner")]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CrewMember(models.Model):
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name="memberships")
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="crew_memberships")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["crew", "employee"], name="unique_crew_employee")]
        ordering = ["position", "pk"]
