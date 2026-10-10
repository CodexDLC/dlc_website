"""Административное чтение клиентского аудита и ручное назначение прав."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ClientMembership, CustomerAuditEvent, PlanProposal, SiteReview
from .services import grant_membership


@admin.register(ClientMembership)
class ClientMembershipAdmin(ModelAdmin):
    list_display = ("user", "client", "is_active", "can_manage_projects", "granted_by", "updated_at")
    list_filter = ("client", "is_active", "can_manage_projects")
    search_fields = ("user__username", "client__name")
    exclude = ("granted_by",)

    def save_model(self, request, obj, form, change):
        saved = grant_membership(
            actor=request.user,
            user=obj.user,
            client=obj.client,
            is_active=obj.is_active,
            can_manage_projects=obj.can_manage_projects,
        )
        obj.pk = saved.pk
        obj.granted_by = request.user

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyWorkflowAdmin(ModelAdmin):
    """Решения проходят через клиентские сервисы и фиксируются аудитом."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomerAuditEvent)
class CustomerAuditAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("created_at", "actor", "client", "action", "target_type", "target_id")
    list_filter = ("client", "action")
    search_fields = ("actor__username", "client__name", "action")


@admin.register(PlanProposal)
class PlanProposalAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("site", "status", "proposed_by", "created_at", "decided_by")
    list_filter = ("status",)


@admin.register(SiteReview)
class SiteReviewAdmin(ReadOnlyWorkflowAdmin):
    list_display = ("site", "status", "submitted_by", "submitted_at", "decided_by", "decided_at")
    list_filter = ("status",)
