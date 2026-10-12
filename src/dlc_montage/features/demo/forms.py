"""Forms limit all posted selections to the current demo workspace."""

from typing import ClassVar

from django import forms
from django.forms import formset_factory

from .models import DemoDailyReport, DemoEmployee, DemoWorkType


class WorkTypeSelect(forms.Select):
    """Expose demo calculation metadata to the shared report preview."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        work = getattr(value, "instance", None)
        if work:
            option["attrs"]["data-is-break"] = str(work.is_break).lower()
        return option


class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = DemoWorkType
        fields = ("name_de", "unit", "is_break", "is_active")


class ReportForm(forms.ModelForm):
    workforce = forms.ModelMultipleChoiceField(
        queryset=DemoEmployee.objects.none(),
        label="Mannschaft",
        widget=forms.SelectMultiple(attrs={"data-day-workforce": ""}),
    )
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
        queryset=DemoWorkType.objects.none(),
        label="Tätigkeit",
        empty_label="Tätigkeit auswählen",
        widget=WorkTypeSelect,
    )
    participants = forms.ModelMultipleChoiceField(
        queryset=DemoEmployee.objects.none(),
        label="Mitarbeiter",
        widget=forms.SelectMultiple(attrs={"data-entry-participants": ""}),
    )
    starts_at = forms.TimeField(
        label="Beginn", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M")
    )
    ends_at = forms.TimeField(label="Ende", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M"))
    quantity = forms.DecimalField(label="Menge", initial=1, min_value=0, max_digits=9, decimal_places=2, required=False)
    description = forms.CharField(
        label="Beschreibung",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_type"].queryset = workspace.work_types.filter(is_active=True)
        self.fields["participants"].queryset = workspace.employees.all()

    def clean_quantity(self):
        value = self.cleaned_data.get("quantity")
        return 1 if value is None else value


EntryFormSet = formset_factory(
    EntryForm,
    extra=0,
    min_num=1,
    validate_min=True,
    max_num=100,
    absolute_max=100,
    validate_max=True,
)
