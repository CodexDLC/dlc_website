"""Узкие формы клиентских действий без внутренних полей CRM."""

from decimal import Decimal
from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from features.projects.models import AcObject, Client, ProjectGroup, SiteWorkItem
from features.work_catalog.models import CableRoute, CableType, WorkType


class CustomerGroupForm(forms.ModelForm):
    """Клиент не выбирает заказчика, статус или внутренних ответственных."""

    reason = forms.CharField(label=_("Причина изменения после начала работ"), max_length=2000, required=False)

    class Meta:
        model = ProjectGroup
        fields: ClassVar = [
            "name",
            "address",
            "additional_addresses",
            "capacity_kw",
            "maps_url",
            "starts_on",
            "ends_on",
            "has_ac",
            "has_dc",
        ]
        widgets: ClassVar = {
            "starts_on": forms.DateInput(attrs={"type": "date"}),
            "ends_on": forms.DateInput(attrs={"type": "date"}),
            "additional_addresses": forms.Textarea(attrs={"rows": 3}),
        }


class CustomerSiteForm(forms.ModelForm):
    """Адресные поля без возможности отметить Standort завершённым."""

    reason = forms.CharField(label=_("Причина изменения после начала работ"), max_length=2000, required=False)

    class Meta:
        model = AcObject
        fields: ClassVar = ["name", "address", "project_number"]


class CustomerPdfForm(forms.Form):
    """Форма приватного PDF до проверки сигнатуры сервисом."""

    file = forms.FileField(
        label=_("PDF-Dokument"), widget=forms.ClearableFileInput(attrs={"accept": "application/pdf"})
    )
    caption = forms.CharField(label=_("Beschreibung"), max_length=500, required=False)

    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"] = forms.ModelChoiceField(
            queryset=group.ac_objects.filter(is_active=True), required=False, label=_("Standort")
        )


class MembershipForm(forms.Form):
    """Ручное назначение пользователя компании менеджером."""

    user = forms.ModelChoiceField(queryset=get_user_model().objects.none(), label=_("Benutzer"))
    client = forms.ModelChoiceField(queryset=Client.objects.none(), label=_("Auftraggeber"))
    is_active = forms.BooleanField(required=False, initial=True, label=_("Aktiv"))
    can_manage_projects = forms.BooleanField(required=False, label=_("Projekte verwalten"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(is_active=True, is_superuser=False)
        self.fields["client"].queryset = Client.objects.filter(is_active=True)


class ReasonForm(forms.Form):
    """Явная причина административного решения или замечания заказчика."""

    reason = forms.CharField(label=_("Begründung"), widget=forms.Textarea(attrs={"rows": 3}), max_length=2000)


class ManualItemForm(forms.Form):
    """Отдельная работа из активного AC-каталога без цен и ставок."""

    work_type = forms.ModelChoiceField(queryset=WorkType.objects.none(), label=_("Вид работы"))
    label = forms.CharField(label=_("Название позиции"), max_length=SiteWorkItem._meta.get_field("label").max_length)
    planned_quantity = forms.DecimalField(label=_("Плановый объём"), min_value=Decimal("0.01"), decimal_places=2)
    route = forms.ModelChoiceField(queryset=CableRoute.objects.none(), required=False, label=_("Путь"))
    cable_type = forms.ModelChoiceField(queryset=CableType.objects.none(), required=False, label=_("Тип кабеля"))
    with_underconstruction = forms.BooleanField(required=False, label=_("С Unterkonstruktion"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_type"].queryset = (
            WorkType.objects.for_direction("ac")
            .filter(is_active=True, is_break=False)
            .exclude(unit=WorkType.Unit.HOUR)
            .exclude(calculation_rule__in=(WorkType.CalculationRule.ACTUAL, WorkType.CalculationRule.ZERO))
        )
        self.fields["route"].queryset = CableRoute.objects.filter(is_active=True)
        self.fields["cable_type"].queryset = CableType.objects.filter(is_active=True)
