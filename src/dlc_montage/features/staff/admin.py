"""Административное ведение персонала."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ("last_name", "first_name", "hourly_rate_eur", "employment_status", "is_foreman", "user")
    list_filter = ("employment_status", "is_foreman")
    search_fields = ("first_name", "last_name")
