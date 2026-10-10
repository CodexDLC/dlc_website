from typing import Any

from django.core.paginator import Page, Paginator
from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404

from ..models import Message, MessageReply


def get_message_queryset() -> QuerySet[Message]:
    return Message.objects.filter(is_archived=False)


def get_messages(status: str | None = None, topic: str | None = None) -> QuerySet[Message]:
    qs = get_message_queryset()
    if status and status != "all":
        qs = qs.filter(status=status)
    if topic:
        qs = qs.filter(topic=topic)
    return qs.order_by("-created_at")


def get_message(pk: int) -> Message | None:
    return Message.objects.filter(pk=pk, is_archived=False).first()


def get_message_or_404(pk: int) -> Message:
    return get_object_or_404(Message, pk=pk, is_archived=False)


def get_replies(message_id: int) -> QuerySet[MessageReply]:
    return MessageReply.objects.filter(message_id=message_id).select_related("sent_by").order_by("sent_at")


def get_topic_counts() -> list[dict[str, Any]]:
    return list(
        Message.objects.filter(is_archived=False).exclude(status=Message.Status.SPAM)
        .values("topic")
        .annotate(count=Count("id"))
        .order_by("topic")
    )


def get_status_counts() -> dict[str, int]:
    """
    Returns counts for all statuses in a single query.
    """
    return Message.objects.filter(is_archived=False).aggregate(
        open=Count("id", filter=Q(status=Message.Status.OPEN)),
        processed=Count("id", filter=Q(status=Message.Status.PROCESSED)),
        spam=Count("id", filter=Q(status=Message.Status.SPAM)),
    )


def get_unread_count() -> int:
    return Message.objects.filter(is_archived=False, is_read=False).count()


def get_paginated_messages(
    *,
    status: str | None = None,
    topic: str | None = None,
    page: str | int | None = None,
    per_page: int = 50,
) -> Page[Message]:
    qs = get_messages(status=status, topic=topic)
    return Paginator(qs, per_page).get_page(page)
