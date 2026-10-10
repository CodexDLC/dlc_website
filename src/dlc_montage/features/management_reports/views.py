"""Месячный контроль и выгрузка внутренних часов."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from features.internal_time.policies import is_manager

from .exports import build_month_workbook
from .forms import MonthForm
from .selectors import monthly_summary


@login_required
def monthly(request):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "staff"
    form = MonthForm(request.GET or {"month": timezone.localdate().strftime("%Y-%m")})
    summary = None
    if form.is_valid():
        month = form.cleaned_data["month"]
        summary = monthly_summary(month.year, month.month)
        if request.GET.get("export") == "xlsx":
            response = HttpResponse(
                build_month_workbook(summary),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="interne-stunden-{month:%Y-%m}.xlsx"'
            response["Cache-Control"] = "private, no-store"
            return response
    return render(request, "management_reports/month.html", {"form": form, "summary": summary})
