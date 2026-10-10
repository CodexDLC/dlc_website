from django.db.models import QuerySet

from .models import Employee


def list_active_employees() -> QuerySet[Employee]:
    return Employee.objects.filter(employment_status=Employee.EmploymentStatus.ACTIVE)


def get_employee_for_user(user: object) -> Employee | None:
    if not getattr(user, "is_authenticated", False):
        return None
    return Employee.objects.filter(user=user).first()
