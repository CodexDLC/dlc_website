

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from features.conversations.selector import (
    get_message,
    get_message_or_404,
    get_message_queryset,
    get_paginated_messages,
    get_replies,
    get_status_counts,
    get_topic_counts,
    get_unread_count,
)
from features.conversations.services.workflow import (
    apply_bulk_action,
    archive_thread,
    create_manual_message,
    create_reply,
    mark_thread_open,
    mark_thread_processed,
    mark_thread_read,
    mark_thread_spam,
    mark_thread_unread,
    trigger_manual_import,
)

_FOLDERS = [
    (reverse_lazy("cabinet:conversations_inbox"), "open", _("Inbox"), "bi-inbox"),
    (reverse_lazy("cabinet:conversations_processed"), "processed", _("Processed"), "bi-check2-circle"),
    (reverse_lazy("cabinet:conversations_all"), "all", _("All"), "bi-collection"),
]


@dataclass
class ConversationsService:
    """Page-service contract for cabinet conversations pages.

    Reads:
        feature selectors under ``features.conversations.selector``
    Writes:
        feature workflow helpers under ``features.conversations.services.workflow``
    """

    @staticmethod
    def get_inbox_context(request: HttpRequest, *, default_folder: str = "open") -> dict[str, Any]:
        """Return a fully assembled inbox page contract."""
        folder = request.GET.get("folder", default_folder)
        topic = request.GET.get("topic", "")
        page_obj = get_paginated_messages(
            status=folder,
            topic=topic or None,
            page=request.GET.get("page"),
            per_page=50,
        )
        return {
            "messages": page_obj,
            "page_obj": page_obj,
            "topics": get_topic_counts(),
            "stats": get_status_counts(),
            "active_folder": folder,
            "active_topic": topic,
            "unread_messages_count": get_unread_count(),
            "folders": _FOLDERS,
            "today": timezone.now().date(),
        }

    @staticmethod
    def get_thread_context(*, pk: int) -> dict[str, Any]:
        message = get_message(pk)
        return {
            "message": message,
            "replies": get_replies(pk),
            "thread_actions": _build_thread_actions(message),
        }

    @staticmethod
    def reply_to_thread(*, pk: int, body: str, user: object) -> dict[str, Any]:
        message = get_message_or_404(pk)
        if body:
            create_reply(message=message, body=body, user=user)
        return {
            "ok": True,
            "code": "reply-created" if body else "reply-empty",
            "message": _("Reply saved.") if body else _("Reply body was empty."),
            "redirect_url": reverse("cabinet:conversations_thread", kwargs={"pk": pk}),
            "meta": {"thread_id": pk},
        }

    @staticmethod
    def perform_thread_action(*, pk: int, action: str) -> dict[str, Any]:
        message = get_message_or_404(pk)
        handlers = {
            "mark_read": (mark_thread_read, _("Thread marked as read."), "thread-marked-read"),
            "mark_unread": (mark_thread_unread, _("Thread marked as unread."), "thread-marked-unread"),
            "mark_processed": (
                mark_thread_processed,
                _("Thread marked as processed."),
                "thread-marked-processed",
            ),
            "mark_open": (mark_thread_open, _("Thread moved back to inbox."), "thread-marked-open"),
            "mark_spam": (mark_thread_spam, _("Thread marked as spam."), "thread-marked-spam"),
            "archive": (archive_thread, _("Thread archived."), "thread-archived"),
        }
        if action not in handlers:
            return {
                "ok": False,
                "code": "thread-action-invalid",
                "message": _("Unsupported thread action."),
                "redirect_url": reverse("cabinet:conversations_thread", kwargs={"pk": pk}),
                "meta": {"thread_id": pk, "action": action},
            }
        handler, success_message, code = handlers[action]
        handler(message=message)
        redirect_url = reverse("cabinet:conversations_thread", kwargs={"pk": pk})
        if action in {"archive", "mark_spam"}:
            redirect_url = reverse("cabinet:conversations_inbox")
        return {
            "ok": True,
            "code": code,
            "message": success_message,
            "redirect_url": redirect_url,
            "meta": {"thread_id": pk, "action": action},
        }

    @staticmethod
    def compose_message(*, request: HttpRequest) -> dict[str, Any]:
        to_email = request.POST.get("to_email", "").strip()
        subject = request.POST.get("subject", "").strip()
        body = request.POST.get("body", "").strip()
        if not to_email or not body:
            return {
                "ok": False,
                "code": "compose-invalid",
                "message": _("Recipient email and body are required."),
                "redirect_url": reverse("cabinet:conversations_compose"),
            }

        message = create_manual_message(
            to_email=to_email,
            subject=subject,
            body=body,
            user=request.user,
        )
        return {
            "ok": True,
            "code": "compose-created",
            "message": _("Message created."),
            "redirect_url": reverse("cabinet:conversations_thread", kwargs={"pk": message.pk}),
            "meta": {"thread_id": message.pk},
        }

    @staticmethod
    def perform_bulk_action(*, request: HttpRequest) -> dict[str, Any]:
        action = request.POST.get("action", "").strip()
        selected_ids = [value for value in request.POST.getlist("message_ids") if value]
        if not action:
            return _result(
                ok=False,
                code="bulk-action-missing",
                message=_("Bulk action is required."),
                redirect_url=_build_inbox_redirect(request),
            )
        if not selected_ids:
            return _result(
                ok=False,
                code="bulk-selection-empty",
                message=_("Select at least one thread."),
                redirect_url=_build_inbox_redirect(request),
            )
        if action not in {"mark_read", "mark_unread", "mark_processed", "mark_open", "mark_spam", "archive"}:
            return _result(
                ok=False,
                code="bulk-action-invalid",
                message=_("Unsupported bulk action."),
                redirect_url=_build_inbox_redirect(request),
            )

        messages_list = list(get_message_queryset().filter(pk__in=selected_ids))
        updated_count = apply_bulk_action(messages=messages_list, action=action)
        return _result(
            ok=True,
            code=f"bulk-{action}",
            message=_("%(count)s threads updated.") % {"count": updated_count},
            redirect_url=_build_inbox_redirect(request),
            meta={"action": action, "updated_count": updated_count},
        )

    @staticmethod
    def check_inbox() -> dict[str, Any]:
        result = trigger_manual_import()
        result["redirect_url"] = reverse("cabinet:conversations_inbox")
        return result


def _build_thread_actions(message: Any) -> list[dict[str, str]]:
    if message is None:
        return []
    actions: list[dict[str, str]] = []
    if message.status != "processed":
        actions.append({"slug": "mark_processed", "label": str(_("Mark as processed"))})
    actions.append(
        {
            "slug": "mark_unread" if message.is_read else "mark_read",
            "label": str(_("Mark as unread") if message.is_read else _("Mark as read")),
        }
    )
    actions.append(
        {
            "slug": "mark_open" if message.status != "open" else "mark_spam",
            "label": str(_("Move to inbox") if message.status != "open" else _("Mark as spam")),
        }
    )
    actions.append({"slug": "archive", "label": str(_("Archive"))})
    return actions


def _build_inbox_redirect(request: HttpRequest) -> str:
    base_url = reverse("cabinet:conversations_inbox")
    params = request.GET.copy()
    folder = request.POST.get("folder", request.GET.get("folder", "open"))
    topic = request.POST.get("topic", request.GET.get("topic", ""))
    if folder:
        params["folder"] = folder
    if topic:
        params["topic"] = topic
    query_string = params.urlencode()
    return f"{base_url}?{query_string}" if query_string else base_url


def _result(
    *,
    ok: bool,
    code: str,
    message: object,
    redirect_url: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "code": code,
        "message": message,
        "redirect_url": redirect_url,
        "meta": meta or {},
    }
