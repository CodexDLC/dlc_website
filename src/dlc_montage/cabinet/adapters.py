from typing import Any, cast

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CabinetAccountAdapter(DefaultAccountAdapter):  # type: ignore[misc]
    """
    Redirect users after login based on their role.

    Settings:
        CABINET_DEFAULT_URL — where staff/superuser go (default: "/cabinet/")
        CABINET_CLIENT_URL  — where regular users go (default: None → same as default)
    """

    def get_login_redirect_url(self, request: Any) -> str:
        default_url = cast(str, getattr(settings, "CABINET_DEFAULT_URL", "/cabinet/"))
        client_url = cast(str, getattr(settings, "CABINET_CLIENT_URL", ""))

        if client_url and not (request.user.is_staff or request.user.is_superuser):
            return client_url
        return default_url
