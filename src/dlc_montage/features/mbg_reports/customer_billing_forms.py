"""Forms for explicit customer billing mappings."""

from django import forms
from django.db.models import Q

from features.projects.models import SiteWorkItem
from features.work_catalog.models import CustomerWorkPosition


class CustomerPackageForm(forms.Form):
    position = forms.ModelChoiceField(label="Kundenposition", queryset=CustomerWorkPosition.objects.none())
    label = forms.CharField(label="Bezeichnung am Standort", max_length=255)
    quantity = forms.DecimalField(
        label="Abrechnungsmenge", max_digits=8, decimal_places=2, required=False, min_value=0.01
    )
    items = forms.ModelMultipleChoiceField(
        label="Zugeordnete Arbeiten",
        queryset=SiteWorkItem.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    manual_confirmed = forms.BooleanField(label="Menge und Ausführung manuell bestätigen", required=False)
    note = forms.CharField(label="Begründung / Aufmaß", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    is_active = forms.BooleanField(label="Aktiv", required=False, initial=True)

    def __init__(self, *args, site, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["position"].queryset = CustomerWorkPosition.objects.filter(
            Q(is_active=True) | Q(pk=instance.position_id if instance else None)
        ).order_by("sort_order", "code")
        existing_ids = instance.work_items.values_list("pk", flat=True) if instance else ()
        self.fields["items"].queryset = (
            SiteWorkItem.objects.filter(site=site)
            .filter(Q(is_required=True) | Q(pk__in=existing_ids))
            .select_related("work_type")
        )
        if instance and not self.is_bound:
            self.initial.update(
                {
                    name: getattr(instance, name)
                    for name in ("position", "label", "quantity", "manual_confirmed", "note", "is_active")
                }
            )
            self.initial["items"] = instance.work_items.values_list("pk", flat=True)
