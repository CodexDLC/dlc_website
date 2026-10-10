"""Редактирование утверждённых двуязычных названий работ."""

from django.contrib import admin

from .models import WorkDescriptionTranslation


@admin.register(WorkDescriptionTranslation)
class WorkDescriptionTranslationAdmin(admin.ModelAdmin):
    list_display = ("original", "name_de", "name_ru")
    search_fields = ("original", "name_de", "name_ru")
