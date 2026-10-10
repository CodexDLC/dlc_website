from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..models.seo import StaticPageSeo


@admin.register(StaticPageSeo)
class StaticPageSeoAdmin(admin.ModelAdmin):
    """Admin for static page SEO entries."""

    list_display = ("page_key", "seo_title", "updated_at")
    list_filter = ("page_key",)
    search_fields = ("seo_title", "seo_description")

    fieldsets = (
        (None, {
            "fields": ("page_key",)
        }),
        (_("SEO Мета-теги"), {
            "fields": ("seo_title", "seo_description", "seo_image")
        }),
        (_("Системная информация"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    readonly_fields = ("created_at", "updated_at")
