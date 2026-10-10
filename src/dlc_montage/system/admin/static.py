from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..models import StaticTranslation


@admin.register(StaticTranslation)
class StaticTranslationAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key", "content")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("key", "content")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
