from typing import ClassVar

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from .models import Message, MessageReply


class MessageReplyInline(TabularInline):
    model = MessageReply
    extra = 0
    fields = ("sent_by", "body", "is_inbound", "sent_at")
    readonly_fields = ("sent_at",)


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ("sender_name", "sender_email", "topic", "status", "source", "channel", "created_at")
    list_filter = ("status", "topic", "source", "channel")
    search_fields = ("sender_name", "sender_email", "sender_phone", "subject", "body")
    readonly_fields = ("thread_key", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines: ClassVar[list] = [MessageReplyInline]

    fieldsets: ClassVar[list] = [
        (_("Sender"), {"fields": ["sender_name", "sender_email", "sender_phone"]}),
        (_("Content"), {"fields": ["subject", "body"]}),
        (_("Classification"), {"fields": ["topic", "status", "source", "channel"]}),
        (_("Meta"), {"fields": ["thread_key", "created_at", "updated_at"], "classes": ["collapse"]}),
    ]
