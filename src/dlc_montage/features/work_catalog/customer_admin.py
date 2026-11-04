from django.contrib import admin

from .models import CustomerWorkPosition


@admin.register(CustomerWorkPosition)
class CustomerWorkPositionAdmin(admin.ModelAdmin):
    list_display = ("code", "name_de", "unit", "unit_price", "manual_only", "is_active")
    search_fields = ("code", "name_de", "name_ru")
    readonly_fields = ("code",)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else ()

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

    def save_model(self, request, obj, form, change):
        from .customer_services import save_customer_position

        saved = save_customer_position(actor=request.user, data=form.cleaned_data, pk=obj.pk if change else None)
        obj.pk = saved.pk
