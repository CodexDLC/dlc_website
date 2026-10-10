"""
Conversation alert helpers.

Outbound send_* methods live here. Cabinet topbar notifications are provided
through the feature registration layer, not from this module.
"""

import logging
from functools import lru_cache

from codex_django.notifications import (
    BaseNotificationEngine,
    DjangoDirectAdapter,
    DjangoQueueAdapter,
    NotificationDispatchSpec,
    notification_handler,
)
from django.conf import settings
from django.utils.translation import gettext_lazy as _

_HAS_ARQ = bool(getattr(settings, "ARQ_REDIS_URL", None) or getattr(settings, "REDIS_URL", None))
log = logging.getLogger(__name__)


def notify_new_message(message) -> None:
    """
    Notify staff that a new contact-form message has arrived.
    Fire-and-forget: routes through the shared notification engine and uses
    queue delivery when ARQ is configured.
    """
    try:
        _get_notification_engine().dispatch_event("conversations.new_message", message)
    except Exception:
        log.exception("Failed to dispatch new message notification for message_id=%s", message.pk)


def notify_thread_reply(message, reply) -> None:
    """Dispatch an outbound reply through the shared notification engine."""
    try:
        _get_notification_engine().dispatch_event("conversations.thread_reply", message, reply)
    except Exception:
        log.exception("Failed to dispatch thread reply notification for message_id=%s", message.pk)


class _StaticSubjectSelector:
    """Fallback selector for domains that provide fully rendered subjects."""

    def get(self, key: str, language: str = "de") -> str | None:
        return None


@lru_cache(maxsize=1)
def _get_notification_engine() -> BaseNotificationEngine:
    queue_adapter = _build_queue_adapter()
    return BaseNotificationEngine(
        queue_adapter=queue_adapter,
        cache_adapter=None,
        i18n_adapter=None,
        selector=_StaticSubjectSelector(),
    )


def _build_queue_adapter():
    if _HAS_ARQ:
        from core.arq.client import arq_client

        return DjangoQueueAdapter(arq_client=arq_client)
    return DjangoDirectAdapter()


@notification_handler("conversations.new_message")
def _build_new_message_specs(message):
    return list(_iter_admin_specs(message))


@notification_handler("conversations.thread_reply")
def _build_thread_reply_specs(message, reply):
    return NotificationDispatchSpec(
        recipient_email=message.sender_email,
        subject_key="conversations.thread_reply.subject",
        subject=_build_reply_subject(message),
        event_type="conversations.thread_reply",
        channels=["email"],
        mode="rendered",
        text_content=reply.body,
        context=_build_reply_context(message, reply),
    )


def _iter_admin_specs(message):
    for _, email in getattr(settings, "ADMINS", ()):
        if not email:
            continue
        yield NotificationDispatchSpec(
            recipient_email=email,
            subject_key="conversations.new_message.subject",
            subject=_build_subject(message),
            event_type="conversations.new_message",
            channels=["email"],
            mode="rendered",
            text_content=_build_text_content(message),
        )


def _build_subject(message) -> str:
    preview = message.subject or message.body[:60]
    return _("[New message] %(sender)s - %(preview)s") % {
        "sender": message.sender_name,
        "preview": preview,
    }


def _build_text_content(message) -> str:
    return _(
        "From: %(name)s <%(email)s>\n"
        "Topic: %(topic)s\n"
        "Source: %(source)s\n"
        "Channel: %(channel)s\n\n"
        "%(body)s"
    ) % {
        "name": message.sender_name,
        "email": message.sender_email,
        "topic": message.get_topic_display(),
        "source": message.get_source_display(),
        "channel": message.get_channel_display(),
        "body": message.body,
    }


def _build_reply_subject(message) -> str:
    subject = message.subject.strip() if message.subject else ""
    if not subject:
        return _("Re: Conversation %(thread)s") % {"thread": message.thread_key[:8]}
    if subject.lower().startswith("re:"):
        return subject
    return _("Re: %(subject)s") % {"subject": subject}


def _build_reply_context(message, reply) -> dict[str, object]:
    from .email_import import build_mailbox_correlation_data

    correlation = build_mailbox_correlation_data(thread_key=message.thread_key)
    return {
        "message_id": message.pk,
        "reply_id": reply.pk,
        "thread_key": correlation.thread_key,
        "reply_match_token": correlation.reply_match_token,
    }
