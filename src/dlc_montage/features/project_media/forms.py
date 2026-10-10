from core.forms import LocalizedFormMixin
from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from features.projects.widgets import SearchableSelect

from .models import ProjectFile


class UploadForm(LocalizedFormMixin, forms.Form):
    file = forms.FileField(
        label=_("Файл"),
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp,application/pdf"}),
    )
    kind = forms.ChoiceField(label=_("Назначение"), choices=ProjectFile._meta.get_field("kind").choices)
    caption = forms.CharField(label=_("Подпись"), max_length=500, required=False)

    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"] = forms.ModelChoiceField(
            label=_("AC-объект"),
            required=False,
            queryset=group.ac_objects.filter(is_active=True),
            empty_label=_("Общий проект / DC"),
            widget=SearchableSelect(
                kind="site",
                search_url=reverse_lazy("projects:site_choices"),
                fixed_group=str(group.pk),
                placeholder=_("Общий проект или поиск Standort"),
            ),
        )


class MediaFilterForm(LocalizedFormMixin, forms.Form):
    kind = forms.ChoiceField(
        label=_("Тип файла"),
        required=False,
        choices=[("", _("Все типы")), *ProjectFile._meta.get_field("kind").choices],
    )
    site = forms.ChoiceField(label=_("Объект"), required=False)

    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].choices = [
            ("", _("Все объекты")),
            ("general", _("Общие файлы проекта")),
            *((str(site.pk), str(site)) for site in group.ac_objects.filter(is_active=True)),
        ]
        self.fields["site"].widget = SearchableSelect(
            kind="site",
            search_url=reverse_lazy("projects:site_choices"),
            fixed_group=str(group.pk),
            placeholder=_("Все объекты — начните вводить для поиска"),
            choices=self.fields["site"].choices,
        )
