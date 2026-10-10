"""Редактирование работников без перехода в техническую админку."""

from typing import ClassVar

from core.forms import LocalizedFormMixin
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Employee


class EmployeeForm(LocalizedFormMixin, forms.ModelForm):
    class Meta:
        model = Employee
        fields: ClassVar = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "hourly_rate_eur",
            "employment_status",
            "is_foreman",
            "has_ac_access",
            "has_dc_access",
            "user",
        ]
        labels: ClassVar = {
            "first_name": _("Имя"),
            "last_name": _("Фамилия"),
            "phone": _("Телефон"),
            "email": _("Электронная почта"),
            "hourly_rate_eur": _("Почасовая ставка brutto, €"),
            "employment_status": _("Статус"),
            "is_foreman": _("Бригадир"),
            "has_ac_access": _("Доступ AC"),
            "has_dc_access": _("Доступ DC"),
            "user": _("Учётная запись"),
        }
