"""Progressively enhanced, server-backed choice widgets."""

from django import forms
from django.utils.translation import gettext_lazy as _


class SearchableSelect(forms.Select):
    """Keep a native select as fallback and expose remote search metadata."""

    def __init__(
        self,
        *,
        kind,
        search_url,
        parent="",
        direction="",
        direction_source="",
        fixed_group="",
        placeholder="",
        empty_text="",
        attrs=None,
        choices=(),
    ):
        widget_attrs = {
            "data-searchable-choice": kind,
            "data-search-url": search_url,
            "data-search-parent": parent,
            "data-search-direction": direction,
            "data-search-direction-source": direction_source,
            "data-search-fixed-group": fixed_group,
            "data-search-placeholder": placeholder or _("Поиск"),
            "data-search-empty": empty_text or _("Ничего не найдено"),
        }
        widget_attrs.update(attrs or {})
        super().__init__(attrs=widget_attrs, choices=choices)
