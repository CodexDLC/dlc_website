"""Справочник работ доступен администратору; отчёты изменяются через сервисы CRM."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import WorkType


@admin.register(WorkType)
class WorkTypeAdmin(ModelAdmin):
    search_fields = ("name",)
