"""Справочники заказчиков и общих проектов."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AcObject, Client, ProjectGroup


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    search_fields = ("name",)


@admin.register(ProjectGroup)
class ProjectGroupAdmin(ModelAdmin):
    list_display = ("name", "client", "has_ac", "has_dc", "status", "responsible")
    search_fields = ("name", "address")
    list_filter = ("status", "has_ac", "has_dc")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AcObject)
class AcObjectAdmin(ModelAdmin):
    list_display = ("name", "group", "project_number", "is_active")
    search_fields = ("name", "address", "project_number")
    list_filter = ("is_active",)

    def has_delete_permission(self, request, obj=None):
        return False
