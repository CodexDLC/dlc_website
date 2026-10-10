"""Управление названиями работ."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from features.internal_time.policies import is_manager

from .forms import WorkTypeForm
from .models import WorkType
from .services import save_work_type


@login_required
def catalog(request, pk=None):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "administration"
    obj = get_object_or_404(WorkType, pk=pk) if pk else None
    form = WorkTypeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            save_work_type(actor=request.user, data=form.cleaned_data, pk=pk)
            return redirect("work_catalog:list")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "work_catalog/list.html", {"items": WorkType.objects.all(), "form": form})
