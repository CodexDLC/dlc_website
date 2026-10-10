"""Формы ручного переноса бумажных листов."""

from decimal import Decimal
from uuid import uuid4

from core.forms import LocalizedFormMixin
from django import forms
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.selectors import active_ac_groups, active_ac_objects_for_group
from features.projects.widgets import SearchableSelect
from features.staff.models import Employee
from features.work_catalog.models import CableRoute, CableType, WorkType

from .models import MbgDailyReport


class WorkTypeSelect(forms.Select):
    """Передать браузеру требования выбранной позиции каталога."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        work = getattr(value, "instance", None)
        if work:
            option["attrs"]["data-requires-route"] = str(work.requires_route).lower()
            option["attrs"]["data-requires-cable"] = str(work.requires_cable_type).lower()
        return option


class WorkItemSelect(forms.Select):
    """Передать браузеру идентичность выбранной плановой позиции."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        item = getattr(value, "instance", None)
        if item:
            option["attrs"].update(
                {
                    "data-work-type": item.work_type_id,
                    "data-route": item.route_id or "",
                    "data-cable-type": item.cable_type_id or "",
                    "data-underconstruction": str(item.with_underconstruction).lower(),
                }
            )
        return option


class SiteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} · P/Nr {obj.project_number or '—'}"


class ReportForm(LocalizedFormMixin, forms.Form):
    group = forms.ModelChoiceField(
        label=_("Проект"),
        queryset=ProjectGroup.objects.none(),
        widget=SearchableSelect(
            kind="group",
            search_url=reverse_lazy("projects:group_choices"),
            direction="ac",
            placeholder=_("Начните вводить название, адрес или заказчика"),
            attrs={
                "data-mbg-group": "",
                "hx-get": reverse_lazy("mbg_reports:site_options"),
                "hx-trigger": "change",
                "hx-target": "#mbg-site-field",
                "hx-swap": "outerHTML",
            },
        ),
    )
    site = SiteChoiceField(
        label=_("Объект"),
        queryset=AcObject.objects.none(),
        widget=SearchableSelect(
            kind="site",
            search_url=reverse_lazy("projects:site_choices"),
            parent="#id_group",
            placeholder=_("Начните вводить Standort, адрес или P/Nr"),
            attrs={"data-mbg-site": ""},
        ),
    )
    work_date = forms.DateField(
        label=_("Дата"),
        initial=timezone.localdate,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    workforce = forms.ModelMultipleChoiceField(
        label=_("Состав рабочего дня"),
        queryset=Employee.objects.filter(employment_status="active", has_ac_access=True),
        widget=forms.SelectMultiple(attrs={"data-day-workforce": ""}),
    )
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)
    submission_key = forms.UUIDField(initial=uuid4, widget=forms.HiddenInput)
    reason = forms.CharField(
        label=_("Причина исправления / комментарий"),
        required=False,
        error_messages={"required": _("Укажите причину исправления принятого отчёта.")},
    )

    def __init__(self, *args, require_reason=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].required = require_reason
        self.fields["group"].queryset = active_ac_groups()
        group_id = self._selected_group_id()
        self.fields["site"].queryset = active_ac_objects_for_group(group_id)
        if not group_id:
            self.fields["site"].widget.attrs["disabled"] = True

    def _selected_group_id(self):
        if self.is_bound:
            return self.data.get(self.add_prefix("group"))
        group = self.initial.get("group")
        return getattr(group, "pk", group)


class ReportListFilterForm(LocalizedFormMixin, forms.Form):
    group = forms.ModelChoiceField(
        label=_("Проект"),
        queryset=ProjectGroup.objects.none(),
        required=False,
        empty_label=_("Все проекты"),
        widget=SearchableSelect(
            kind="group",
            search_url=reverse_lazy("projects:group_choices"),
            direction="ac",
            placeholder=_("Все проекты — начните вводить для поиска"),
        ),
    )
    site = SiteChoiceField(
        label=_("Объект"),
        queryset=AcObject.objects.none(),
        required=False,
        empty_label=_("Все объекты"),
        widget=SearchableSelect(
            kind="site",
            search_url=reverse_lazy("projects:site_choices"),
            parent="#id_group",
            placeholder=_("Все объекты — выберите проект или введите адрес"),
        ),
    )
    status = forms.ChoiceField(
        label=_("Статус"),
        required=False,
        choices=(("", _("Все статусы")), *MbgDailyReport._meta.get_field("status").choices),
    )
    date_from = forms.DateField(
        label=_("Дата с"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("Дата по"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].queryset = ProjectGroup.objects.filter(has_ac=True)
        group_id = self.data.get(self.add_prefix("group")) if self.is_bound else None
        self.fields["site"].queryset = (
            AcObject.objects.filter(group_id=group_id).select_related("group")
            if group_id and str(group_id).isdigit()
            else AcObject.objects.none()
        )
        if not group_id:
            self.fields["site"].widget.attrs["disabled"] = True
        self.fields["group"].empty_label = _("Все проекты")
        self.fields["site"].empty_label = _("Все объекты")

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", _("Конечная дата не может быть раньше начальной."))
        return cleaned


class EntryForm(LocalizedFormMixin, forms.Form):
    participants = forms.ModelMultipleChoiceField(
        label=_("Кто выполнял"),
        queryset=Employee.objects.filter(employment_status="active", has_ac_access=True),
        widget=forms.SelectMultiple(attrs={"data-entry-participants": ""}),
    )
    starts_at = forms.TimeField(label=_("Начало"), widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    ends_at = forms.TimeField(label=_("Окончание"), widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    work_type = forms.ModelChoiceField(
        label=_("Вид работы"),
        queryset=WorkType.objects.for_direction("ac").filter(is_active=True),
        widget=WorkTypeSelect,
    )
    work_item = forms.ModelChoiceField(
        label=_("Позиция плана Standort"),
        queryset=SiteWorkItem.objects.none(),
        required=False,
        widget=WorkItemSelect(attrs={"data-work-item": ""}),
    )
    completed_quantity = forms.DecimalField(
        label=_("Прирост выполненного объёма"),
        min_value=Decimal("0"),
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )
    quantity = forms.DecimalField(label=_("Количество"), min_value=Decimal("0.01"), decimal_places=2, initial=1)
    cable_type = forms.ModelChoiceField(
        label=_("Тип кабеля"), queryset=CableType.objects.filter(is_active=True), required=False
    )
    route = forms.ModelChoiceField(label=_("Путь"), queryset=CableRoute.objects.filter(is_active=True), required=False)
    standard_connections = forms.IntegerField(label=_("Обычные подключения"), min_value=0, initial=0)
    heavy_connections = forms.IntegerField(label=_("Тяжёлые подключения"), min_value=0, initial=0)
    with_underconstruction = forms.BooleanField(label=_("С монтажной конструкцией"), required=False)
    description = forms.CharField(label=_("Свой текст на немецком"), max_length=500, required=False)
    internal_only = forms.BooleanField(
        label=_("Только внутренний учёт / Nur interne Zeiterfassung"), required=False, initial=False
    )

    def __init__(self, *args, site_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_item"].queryset = (
            SiteWorkItem.objects.filter(site_id=site_id).select_related("work_type", "route", "cable_type")
            if str(site_id or "").isdigit()
            else SiteWorkItem.objects.none()
        )

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("work_item") is None) != (cleaned.get("completed_quantity") is None):
            raise forms.ValidationError(_("Позиция плана и прирост объёма вводятся вместе."))
        return cleaned


EntryFormSet = forms.formset_factory(
    EntryForm, extra=0, min_num=1, validate_min=True, max_num=100, validate_max=True, absolute_max=100
)


class WeekForm(LocalizedFormMixin, forms.Form):
    year = forms.IntegerField(label=_("Год"), min_value=2000, max_value=2100)
    week = forms.IntegerField(label=_("Календарная неделя"), min_value=1, max_value=53)
