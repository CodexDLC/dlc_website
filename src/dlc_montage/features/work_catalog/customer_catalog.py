"""Customer position maintenance."""

from typing import ClassVar

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from features.mbg_reports.policies import can_export_reports

from .customer_selectors import all_customer_positions
from .customer_services import save_customer_position
from .models import CustomerWorkPosition


class CustomerPositionForm(forms.ModelForm):
    class Meta:
        model = CustomerWorkPosition
        fields = ("code", "name_de", "name_ru", "unit", "unit_price", "manual_only", "sort_order", "is_active", "note")
        labels: ClassVar = {
            "code": "Positionsnummer",
            "name_de": "Bezeichnung (Deutsch)",
            "name_ru": "Bezeichnung (Russisch)",
            "unit": "Einheit",
            "unit_price": "Preis (€)",
            "manual_only": "Nur manuelle Zuordnung",
            "sort_order": "Reihenfolge",
            "is_active": "Aktiv",
            "note": "Hinweis",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["code"].disabled = True


@login_required
def customer_catalog(request, pk=None):
    if not can_export_reports(request.user):
        raise PermissionDenied
    request.cabinet_module = "administration"
    obj = get_object_or_404(CustomerWorkPosition, pk=pk) if pk else None
    form = CustomerPositionForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            save_customer_position(actor=request.user, data=form.cleaned_data, pk=pk)
            return redirect("work_catalog:customer_list")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request, "work_catalog/customer_catalog.html", {"items": all_customer_positions(), "form": form, "editing": obj}
    )
