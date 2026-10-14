"""Запрет внутренних CRM-маршрутов для клиентской учётной записи."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from features.internal_time.policies import is_manager

from .models import ClientMembership


class CustomerBoundaryMiddleware:
    """Защитить прямые ссылки вне клиентского пространства, включая файлы."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or is_manager(request.user):
            return None
        if not ClientMembership.objects.filter(user=request.user).exists():
            return None
        parts = [part for part in request.path_info.split("/") if part]
        if parts and (len(parts[0]) == 2 or parts[0].lower() in {"de-de", "en-us", "ru-ru"}):
            parts = parts[1:]
        if not parts:
            return None
        if parts[0] == "cabinet":
            if len(parts) == 1:
                return redirect("customer_portal:home")
            if parts[1] in {"customer", "demo", "photos", "login", "logout", "password"}:
                return None
            raise PermissionDenied
        if parts[0] in {"admin", "system", "conversations"}:
            raise PermissionDenied
        return None
