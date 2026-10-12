"""Forms limit all posted selections to the current demo workspace."""

from typing import ClassVar

from django import forms
from django.forms import formset_factory

from .models import DemoDailyReport, DemoEmployee, DemoWorkType


class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = DemoWorkType
        fields = ("name_de", "unit", "is_break", "is_active")


class ReportForm(forms.ModelForm):
    workforce = forms.ModelMultipleChoiceField(queryset=DemoEmployee.objects.none(), label="Mannschaft")
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = DemoDailyReport
        fields = ("date", "site_name", "address", "project_number", "workforce")
        widgets: ClassVar = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workforce"].queryset = workspace.employees.all()
        self.fields["version"].initial = self.instance.version if self.instance.pk else None


class EntryForm(forms.Form):
    work_type = forms.ModelChoiceField(
        queryset=DemoWorkType.objects.none(), label="Tätigkeit", empty_label="Tätigkeit auswählen"
    )
    participants = forms.ModelMultipleChoiceField(queryset=DemoEmployee.objects.none(), label="Mitarbeiter")
    starts_at = forms.TimeField(
        label="Beginn", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M")
    )
    ends_at = forms.TimeField(label="Ende", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M"))
    quantity = forms.DecimalField(label="Menge", initial=1, min_value=0, max_digits=9, decimal_places=2, required=False)
    description = forms.CharField(label="Beschreibung", max_length=1000, required=False)

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_type"].queryset = workspace.work_types.filter(is_active=True)
        self.fields["participants"].queryset = workspace.employees.all()

    def clean_quantity(self):
        value = self.cleaned_data.get("quantity")
        return 1 if value is None else value


EntryFormSet = formset_factory(EntryForm, extra=1, can_delete=True, max_num=100, absolute_max=100, validate_max=True)
