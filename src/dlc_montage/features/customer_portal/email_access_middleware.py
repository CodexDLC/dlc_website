"""Enforce absolute expiry and the customer boundary on every magic session."""

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied

from .email_access_selectors import EMAIL_ACCESS_SESSION_KEY, grant_for_session
from .email_access_views import email_access_page


class CustomerEmailAccessMiddleware:
    """Never let a magic session inherit later staff permissions or leave the portal."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if EMAIL_ACCESS_SESSION_KEY not in request.session:
            return None
        match = request.resolver_match
        is_entry = match.view_name == "customer_portal:email_access"
        is_auth = match.url_name in {"account_login", "account_logout"} and match.namespace != "customer_portal"
        grant = grant_for_session(
            grant_id=request.session[EMAIL_ACCESS_SESSION_KEY],
            user_id=request.user.pk if request.user.is_authenticated else None,
        )
        if grant is None:
            logout(request)
            if is_entry or is_auth:
                return None
            return email_access_page(request, expired=True, status=410)
        if match.namespace == "customer_portal" or is_auth:
            return None
        raise PermissionDenied
