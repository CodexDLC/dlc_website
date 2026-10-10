"""Shared localization for Django forms used by CRM features."""

from django import forms
from django.utils.translation import gettext


class LocalizedFormMixin:
    """Translate labels and literal choices without changing domain values."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.label:
                field.label = gettext(str(field.label))
            if isinstance(field, forms.ModelMultipleChoiceField):
                field.empty_label = None
            elif isinstance(field, forms.ModelChoiceField):
                field.empty_label = gettext("Выберите вариант")
            elif isinstance(field, forms.ChoiceField):
                field.choices = [(value, gettext(str(label))) for value, label in field.choices]
