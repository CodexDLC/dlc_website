from datetime import date

from core.forms import LocalizedFormMixin
from django import forms
from django.utils.translation import gettext_lazy as _


class MonthForm(LocalizedFormMixin, forms.Form):
    month = forms.RegexField(regex=r"^\d{4}-\d{2}$", label=_("Месяц"), widget=forms.TextInput(attrs={"type": "month"}))

    def clean_month(self):
        try:
            return date.fromisoformat(self.cleaned_data["month"] + "-01")
        except ValueError as exc:
            raise forms.ValidationError(_("Укажите корректный месяц.")) from exc
