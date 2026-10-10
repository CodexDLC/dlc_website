from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from features.conversations.models import Message, MessageReply

from .alerts import notify_thread_reply
from .email_import import trigger_email_import


def create_manual_message(*, to_email: str, subject: str, body: str, user: Any) -> Message:
    """Create a manual outbound thread for cabinet compose flow."""
    user_model = get_user_model()
    display_name = user.get_full_name() if isinstance(user, user_model) else ""
    sender_name = display_name or to_email

    with transaction.atomic():
        message = Message.objects.create(
            sender_name=sender_name,
            sender_email=to_email,
            subject=subject,
            body=body,
            source=Message.Source.MANUAL,
            channel=Message.Channel.EMAIL,
            topic=Message.Topic.GENERAL,
            status=Message.Status.PROCESSED,
            is_read=True,
        )
        MessageReply.objects.create(
            message=message,
            body=body,
            sent_by=user if getattr(user, "is_authenticated", False) else None,
            is_inbound=False,
        )
    return message


def create_reply(*, message: Message, body: str, user: Any) -> MessageReply:
    """Persist an outbound reply and update the thread state."""
    with transaction.atomic():
        reply = MessageReply.objects.create(
            message=message,
            body=body,
            sent_by=user if getattr(user, "is_authenticated", False) else None,
            is_inbound=False,
        )
        message.status = Message.Status.PROCESSED
        message.is_read = True
        message.save(update_fields=["status", "is_read", "updated_at"])
    notify_thread_reply(message, reply)
    return reply


def mark_thread_read(*, message: Message) -> Message:
    return _update_message_state(message=message, is_read=True)


def mark_thread_unread(*, message: Message) -> Message:
    return _update_message_state(message=message, is_read=False)


def mark_thread_processed(*, message: Message) -> Message:
    return _update_message_state(message=message, status=Message.Status.PROCESSED, is_read=True)


def mark_thread_open(*, message: Message) -> Message:
    return _update_message_state(message=message, status=Message.Status.OPEN)


def mark_thread_spam(*, message: Message) -> Message:
    return _update_message_state(message=message, status=Message.Status.SPAM, is_read=True)


def archive_thread(*, message: Message) -> Message:
    return _update_message_state(message=message, is_archived=True, is_read=True)


def apply_bulk_action(*, messages: Iterable[Message], action: str) -> int:
    handlers = {
        "mark_read": mark_thread_read,
        "mark_unread": mark_thread_unread,
        "mark_processed": mark_thread_processed,
        "mark_open": mark_thread_open,
        "mark_spam": mark_thread_spam,
        "archive": archive_thread,
    }
    handler = handlers.get(action)
    if handler is None:
        raise ValueError(f"Unsupported bulk action: {action}")

    count = 0
    for message in messages:
        handler(message=message)
        count += 1
    return count


def trigger_manual_import() -> dict[str, object]:
    """Normalize background-import feedback into a stable result contract."""
    result = trigger_email_import()
    mode = result.get("mode", "thread")
    if mode == "queued":
        message = _("Mail check queued in background.")
    else:
        message = _("Mail check started.")
    return {
        "ok": True,
        "code": f"email-import-{mode}",
        "message": str(message),
        "redirect_url": None,
        "meta": result,
    }


def _update_message_state(
    *,
    message: Message,
    status: str | None = None,
    is_read: bool | None = None,
    is_archived: bool | None = None,
) -> Message:
    update_fields = ["updated_at"]
    if status is not None:
        message.status = status
        update_fields.append("status")
    if is_read is not None:
        message.is_read = is_read
        update_fields.append("is_read")
    if is_archived is not None:
        message.is_archived = is_archived
        update_fields.append("is_archived")
    message.save(update_fields=update_fields)
    return message
