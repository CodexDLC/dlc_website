"""Изменения каталога выполняет администратор."""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from features.internal_time.policies import is_manager

from .models import WorkType


@transaction.atomic
def save_work_type(*, actor, data, pk=None):
    if not is_manager(actor):
        raise PermissionDenied
    obj = WorkType.objects.select_for_update().get(pk=pk) if pk else WorkType()
    for field in (
        "code",
        "name_de",
        "name_ru",
        "direction",
        "unit",
        "calculation_rule",
        "normative_hours",
        "price_mode",
        "unit_price",
        "underconstruction_hours",
        "is_break",
        "is_active",
        "sort_order",
    ):
        setattr(obj, field, data[field])
    obj.full_clean()
    obj.save()
    return obj
