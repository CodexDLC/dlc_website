from django.db.models import QuerySet

from features.staff.models import Employee

from .models import Crew


def list_active_crews_for_foreman(foreman: Employee) -> QuerySet[Crew]:
    return Crew.objects.filter(owner=foreman, is_active=True).prefetch_related("memberships__employee")
