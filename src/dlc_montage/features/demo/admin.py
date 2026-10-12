"""Administrative inspection of isolated demo data."""

from django.contrib import admin

from .models import DemoDailyReport, DemoEmployee, DemoWorkEntry, DemoWorkspace, DemoWorkType


@admin.register(DemoWorkspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "created_at")
    readonly_fields = ("owner", "created_at")

    def has_add_permission(self, request):
        return False


class ReadOnlyDemoAdmin(admin.ModelAdmin):
    """Changes must use owner-validated services, including for staff."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register((DemoDailyReport, DemoEmployee, DemoWorkEntry, DemoWorkType), ReadOnlyDemoAdmin)
