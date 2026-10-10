

from __future__ import annotations

from typing import Any

from cabinet.services.conversations import ConversationsService
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView


class InboxView(TemplateView):
    template_name = "cabinet/conversations/inbox.html"
    paginate_by = 50

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        request.cabinet_module = "conversations"
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(ConversationsService.get_inbox_context(self.request))
        return context


class ProcessedView(InboxView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(ConversationsService.get_inbox_context(self.request, default_folder="processed"))
        return context


class AllMessagesView(InboxView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(ConversationsService.get_inbox_context(self.request, default_folder="all"))
        return context


class ThreadView(TemplateView):
    template_name = "cabinet/conversations/thread.html"

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        request.cabinet_module = "conversations"
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(ConversationsService.get_thread_context(pk=self.kwargs["pk"]))
        return context


class ComposeView(TemplateView):
    template_name = "cabinet/conversations/compose.html"

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        request.cabinet_module = "conversations"
        return super().dispatch(request, *args, **kwargs)

    def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        result = ConversationsService.compose_message(request=request)
        return redirect(result["redirect_url"])


class ThreadReplyActionView(TemplateView):
    def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        body = request.POST.get("body", "").strip()
        result = ConversationsService.reply_to_thread(pk=self.kwargs["pk"], body=body, user=request.user)
        return redirect(result["redirect_url"])


class ThreadActionView(TemplateView):
    def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        result = ConversationsService.perform_thread_action(pk=self.kwargs["pk"], action=self.kwargs["action"])
        return redirect(result["redirect_url"])


class InboxBulkActionView(TemplateView):
    def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        result = ConversationsService.perform_bulk_action(request=request)
        return redirect(result["redirect_url"])


def manual_check_view(request: Any) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    result = ConversationsService.check_inbox()
    return redirect(result["redirect_url"])
