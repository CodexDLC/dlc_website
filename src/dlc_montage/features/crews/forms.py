"""Форма сохранённой команды для быстрого заполнения отчётов."""

from django import forms
from django.utils.translation import gettext_lazy as _

from features.internal_time.policies import employee_for, is_manager
from features.staff.models import Employee


class TeamForm(forms.Form):
    name = forms.CharField(label=_("Название команды"), max_length=120)
    owner = forms.ModelChoiceField(label=_("Ответственный бригадир"), queryset=Employee.objects.none())
    members = forms.ModelMultipleChoiceField(
        label=_("Сотрудники"), queryset=Employee.objects.none(), widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, user, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        employees = Employee.objects.filter(employment_status="active")
        self.fields["members"].queryset = employees
        self.fields["owner"].queryset = (
            employees if is_manager(user) else employees.filter(pk=getattr(employee_for(user), "pk", None))
        )
        if not is_manager(user):
            self.fields["owner"].widget = forms.HiddenInput()
            self.fields["owner"].initial = employee_for(user)
