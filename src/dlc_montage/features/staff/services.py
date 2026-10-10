from django.core.exceptions import PermissionDenied
from django.db import transaction

from features.internal_time.policies import is_manager

from .models import Employee


@transaction.atomic
def create_employee(**fields: object) -> Employee:
    return Employee.objects.create(**fields)


@transaction.atomic
def save_employee(*, actor, data, employee_id=None):
    """Создать или отредактировать сотрудника по правам администратора."""
    if not is_manager(actor):
        raise PermissionDenied
    obj = Employee.objects.select_for_update().get(pk=employee_id) if employee_id else Employee()
    for key in (
        "first_name",
        "last_name",
        "phone",
        "email",
        "hourly_rate_eur",
        "employment_status",
        "is_foreman",
        "has_ac_access",
        "has_dc_access",
        "user",
    ):
        setattr(obj, key, data[key])
    obj.full_clean()
    obj.save()
    return obj
