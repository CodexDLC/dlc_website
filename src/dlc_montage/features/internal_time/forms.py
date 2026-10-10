"""Поля редактора общего дня и участников."""

from uuid import uuid4

from django import forms
from django.forms import formset_factory
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.projects.models import ProjectGroup
from features.projects.widgets import SearchableSelect
from features.staff.models import Employee

from .policies import directions_for
from .selectors import available_employees, available_groups


class ReportForm(forms.Form):
    submission_key = forms.UUIDField(initial=uuid4, widget=forms.HiddenInput)
    work_date = forms.DateField(
        label=_("Дата"), initial=timezone.localdate, widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    direction = forms.ChoiceField(label=_("Направление"), choices=[])
    project_group = forms.ModelChoiceField(
        label=_("Проект"),
        queryset=ProjectGroup.objects.none(),
        widget=SearchableSelect(
            kind="group",
            search_url=reverse_lazy("projects:group_choices"),
            direction_source="#id_direction",
            placeholder=_("Начните вводить название, адрес или заказчика"),
        ),
    )
    starts_at = forms.TimeField(
        label=_("Начало"), initial="07:00", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )
    ends_at = forms.TimeField(
        label=_("Окончание"), initial="18:00", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )
    lunch_minutes = forms.IntegerField(label=_("Обед, минут"), min_value=0, initial=30)
    work_description = forms.CharField(
        label=_("Вид работы (необязательно)"),
        max_length=180,
        required=False,
        widget=forms.TextInput(attrs={"list": "work-types"}),
    )
    note = forms.CharField(label=_("Комментарий"), required=False, widget=forms.Textarea(attrs={"rows": 2}))
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)
    reason = forms.CharField(
        label=_("Причина исправления администратором"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("Что и почему исправлено")}),
    )

    def __init__(self, *args, user, report=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direction"].choices = directions_for(user)
        groups = available_groups(user)
        if report:
            groups = ProjectGroup.objects.filter(pk__in=[*groups.values_list("pk", flat=True), report.project_group_id])
        self.fields["project_group"].queryset = groups


class ParticipantForm(forms.Form):
    employee = forms.ModelChoiceField(label=_("Сотрудник"), queryset=Employee.objects.none())
    deduction_minutes = forms.IntegerField(
        label=_("Уменьшить на, минут"), min_value=0, initial=0, widget=forms.NumberInput(attrs={"step": 1})
    )

    def __init__(self, *args, employee_ids=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.filter(
            pk__in=list(available_employees().values_list("pk", flat=True)) + list(employee_ids)
        )


ParticipantFormSet = formset_factory(
    ParticipantForm, extra=0, min_num=1, validate_min=True, max_num=100, validate_max=True, absolute_max=100
)


class QuickProjectForm(forms.Form):
    name = forms.CharField(label=_("Название проекта"), max_length=255)
