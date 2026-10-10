from typing import ClassVar

from core.forms import LocalizedFormMixin
from django import forms

from .models import WorkType


class WorkTypeForm(LocalizedFormMixin, forms.ModelForm):
    class Meta:
        model = WorkType
        fields: ClassVar = [
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
            "sort_order",
            "is_active",
        ]
