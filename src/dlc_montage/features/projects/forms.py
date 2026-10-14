"""Формы карточек проектов и заказчиков."""

from typing import ClassVar

from core.forms import LocalizedFormMixin
from django import forms
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from features.internal_time.policies import is_manager
from features.work_catalog.models import CableRoute, CableType, WorkType

from .models import AcObject, Client, ProjectGroup, SiteWorkItem
from .typical_plan import TypicalPlanConfig


class GroupForm(LocalizedFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectGroup
        exclude: ClassVar = ["created_at"]
        labels: ClassVar = {
            "name": _("Название проекта (Anlage)"),
            "client": _("Заказчик"),
            "capacity_kw": _("Мощность, кВт"),
            "address": _("Основной адрес"),
            "additional_addresses": _("Дополнительные адреса (Standorte / подъезды)"),
            "maps_url": _("Ссылка на Google Maps"),
            "starts_on": _("Дата начала работ"),
            "ends_on": _("Дата завершения работ"),
            "dc_status": _("Готовность DC"),
            "has_ac": _("Работы AC"),
            "has_dc": _("Работы DC"),
            "responsible": _("Главный ответственный"),
            "deputy": _("Заместитель"),
            "ac_responsible": _("Ответственный AC"),
            "dc_responsible": _("Ответственный DC"),
            "status": _("Статус проекта"),
            "edit_level": _("Кто может редактировать"),
        }
        widgets: ClassVar = {
            "starts_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "ends_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "additional_addresses": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _("Например:\\nRomanshorner Weg 206\\nRomanshorner Weg 208\\nRomanshorner Weg 210"),
                }
            ),
            "address": forms.TextInput(attrs={"placeholder": _("Город, улица, номер дома")}),
            "maps_url": forms.URLInput(attrs={"placeholder": "https://maps.google.com/..."}),
            "capacity_kw": forms.NumberInput(attrs={"step": "0.01", "placeholder": _("кВт")}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        # AC progress is derived from Standort reports and completion states.
        self.fields.pop("ac_status", None)
        if not is_manager(user):
            for key in (
                "responsible",
                "deputy",
                "ac_responsible",
                "dc_responsible",
                "edit_level",
                "status",
                "has_ac",
                "has_dc",
            ):
                self.fields.pop(key)


class ObjectForm(LocalizedFormMixin, forms.ModelForm):
    class Meta:
        model = AcObject
        fields: ClassVar = ["name", "address", "project_number", "status", "is_active"]
        labels: ClassVar = {
            "name": _("Дом / подъезд (Standort)"),
            "address": _("Адрес"),
            "project_number": _("Номер проекта заказчика (P/Nr)"),
            "status": _("Готовность Standort"),
            "is_active": _("Активен"),
        }
        widgets: ClassVar = {
            "name": forms.TextInput(attrs={"placeholder": _("Например: Romanshorner Weg 206")}),
            "address": forms.TextInput(attrs={"placeholder": "Romanshorner Weg 206, 13407 Berlin"}),
            "project_number": forms.TextInput(attrs={"placeholder": _("Например: P-12345")}),
        }


class SiteWorkItemForm(LocalizedFormMixin, forms.ModelForm):
    """Параметры физической позиции Standort без расчёта прогресса."""

    class Meta:
        model = SiteWorkItem
        fields: ClassVar = ["label", "work_type", "planned_quantity", "route", "cable_type", "with_underconstruction"]
        labels: ClassVar = {
            "label": _("Название позиции на немецком"),
            "work_type": _("Вид работы"),
            "planned_quantity": _("Плановый объём"),
            "route": _("Путь"),
            "cable_type": _("Тип кабеля"),
            "with_underconstruction": _("С монтажной конструкцией"),
        }

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


class TypicalPlanForm(LocalizedFormMixin, forms.Form):
    """Настройки предварительного типового AC-плана."""

    inverter_count = forms.IntegerField(label=_("Количество Wechselrichter"), min_value=1, max_value=20, initial=1)
    uv_capacity_kw = forms.TypedChoiceField(
        label="UV-PV (kW)",
        choices=[("", "—"), ("25", "25"), ("30", "30"), ("55", "55")],
        coerce=int, empty_value=None, required=False,
    )
    include_nh = forms.BooleanField(label=_("Новый NH-Verteiler"), required=False, initial=True)
    include_nh_hv = forms.BooleanField(label=_("Кабель NH-Verteiler → HV"), required=False)
    wr_underconstruction = forms.BooleanField(label=_("Конструкция для Wechselrichter"), required=False)
    uv_underconstruction = forms.BooleanField(label=_("Конструкция для UV-PV"), required=False)
    nh_underconstruction = forms.BooleanField(label=_("Конструкция для NH-Verteiler"), required=False)
    include_control = forms.BooleanField(label=_("Управление к наружному Schlüsselschalter"), required=False)
    include_trays = forms.BooleanField(label=_("Добавить отдельные Kabeltrassen"), required=False)
    include_hpas_connection = forms.BooleanField(label=_("Добавить подключение к HPAS"), required=False)
    wr_power_cable_code = forms.ChoiceField(label=_("Силовой кабель WR → UV-PV"))
    data_cable_code = forms.ChoiceField(label=_("Кабель данных WR → UV-PV"))
    uv_out_power_cable_code = forms.ChoiceField(label=_("Силовой кабель UV-PV → NH/HV"))
    nh_out_power_cable_code = forms.ChoiceField(label=_("Силовой кабель NH → HV"))
    pe_cable_code = forms.ChoiceField(label="PE-Leitung UV-PV → HPAS")
    control_cable_code = forms.ChoiceField(label=_("Кабель Schlüsselschalter"))
    pe_route_code = forms.ChoiceField(label=_("Путь PE-Leitung к HPAS"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = TypicalPlanConfig()
        categories = {
            "wr_power_cable_code": (CableType.Category.POWER, CableType.Category.HEAVY),
            "data_cable_code": (CableType.Category.DATA,),
            "uv_out_power_cable_code": (CableType.Category.POWER, CableType.Category.HEAVY),
            "nh_out_power_cable_code": (CableType.Category.POWER, CableType.Category.HEAVY),
            "pe_cable_code": (CableType.Category.POTENTIAL,),
            "control_cable_code": (CableType.Category.CONTROL,),
        }
        for field, allowed in categories.items():
            self.fields[field].choices = [
                (cable.code, cable.name_de)
                for cable in CableType.objects.filter(is_active=True, category__in=allowed).order_by("sort_order", "pk")
            ]
            self.fields[field].initial = getattr(defaults, field)
        self.fields["pe_route_code"].choices = [
            (route.code, route.name_de)
            for route in CableRoute.objects.filter(is_active=True, code__in=("uv-hpas-new", "other")).order_by(
                "sort_order", "pk"
            )
        ]
        self.fields["pe_route_code"].initial = defaults.pe_route_code

    def clean(self):
        data = super().clean()
        if data.get("include_nh_hv") and not data.get("include_nh"):
            self.add_error("include_nh_hv", _("Для кабеля NH → HV сначала выберите NH-Verteiler."))
        if data.get("include_control") and data.get("inverter_count") == 1 and data.get("uv_capacity_kw") in {25, 30}:
            self.add_error(
                "include_control",
                "Для UV-PV 25/30 кВт с одним инвертором кабель 7x1,5 не требуется."
                if (get_language() or "").startswith("ru")
                else "Bei UV-PV 25/30 kW mit einem Wechselrichter ist keine Steuerleitung 7x1,5 vorgesehen.",
            )
        return data

    def to_config(self):
        """Вернуть проверенную конфигурацию без обращения к БД."""
        if not self.is_valid():
            raise ValueError(_("Форма типового плана не проверена."))
        return TypicalPlanConfig(**self.cleaned_data)


class ClientForm(LocalizedFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        fields: ClassVar = ["name", "contact_name", "contact_email", "contact_phone", "is_active"]
        labels: ClassVar = {
            "name": _("Название компании"),
            "contact_name": _("Контактное лицо"),
            "contact_email": _("Электронная почта"),
            "contact_phone": _("Телефон"),
            "is_active": _("Активен"),
        }
        widgets: ClassVar = {
            "name": forms.TextInput(attrs={"placeholder": _("Например: MBG Solid Solution GmbH")}),
            "contact_name": forms.TextInput(attrs={"placeholder": _("Имя Фамилия")}),
            "contact_email": forms.EmailInput(attrs={"placeholder": "contact@example.de"}),
            "contact_phone": forms.TextInput(attrs={"placeholder": "+49 ..."}),
        }
