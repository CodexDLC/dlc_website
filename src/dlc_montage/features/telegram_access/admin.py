"""Технический просмотр Telegram-привязок и выданных ссылок."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import TelegramIdentity, TelegramLinkToken


@admin.register(TelegramIdentity)
class TelegramIdentityAdmin(ModelAdmin):
    list_display = ("employee", "telegram_user_id", "username", "is_active", "verified_at")
    list_filter = ("is_active",)
    search_fields = ("employee__first_name", "employee__last_name", "username", "telegram_user_id")
    readonly_fields = ("employee", "telegram_user_id", "private_chat_id", "username", "verified_at", "last_seen_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(ModelAdmin):
    list_display = ("employee", "created_by", "created_at", "expires_at", "used_at", "revoked_at")
    list_filter = ("created_at", "used_at", "revoked_at")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = (
        "employee",
        "token_hash",
        "expires_at",
        "used_at",
        "revoked_at",
        "used_by_telegram_user_id",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
