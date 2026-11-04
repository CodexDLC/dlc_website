"""Authorized changes to customer prices."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from features.mbg_reports.policies import can_export_reports

from .models import CustomerWorkPosition


@transaction.atomic
def save_customer_position(*, actor, data, pk=None):
    if not can_export_reports(actor):
        raise PermissionDenied
    obj = get_object_or_404(CustomerWorkPosition.objects.select_for_update(), pk=pk) if pk else CustomerWorkPosition()
    if pk and data.get("code", obj.code) != obj.code:
        raise ValidationError("Die Positionsnummer kann nicht geändert werden.")
    for field in ("code", "name_de", "name_ru", "unit", "unit_price", "manual_only", "sort_order", "is_active", "note"):
        if field in data:
            setattr(obj, field, data[field])
    obj.full_clean()
    obj.save()
    return obj
