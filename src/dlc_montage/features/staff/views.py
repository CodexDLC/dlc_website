"""Список персонала в рабочем кабинете."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from features.internal_time.policies import can_report, is_manager

from .forms import EmployeeForm
from .models import Employee
from .selectors import list_active_employees
from .services import save_employee


@login_required
def employee_list(request):
    """Показать действующий персонал; записи заводит администратор."""
    if not can_report(request.user):
        raise PermissionDenied
    request.cabinet_module = "staff"
    return render(
        request,
        "staff/employees.html",
        {
            "employees": Employee.objects.all() if is_manager(request.user) else list_active_employees(),
            "manager": is_manager(request.user),
        },
    )


@login_required
def employee_edit(request, pk=None):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "staff"
    obj = get_object_or_404(Employee, pk=pk) if pk else None
    form = EmployeeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            save_employee(actor=request.user, data=form.cleaned_data, employee_id=pk)
            return redirect("staff_employees")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "cabinet/components/entity_form.html", {"form": form, "title": _("Карточка сотрудника")})
