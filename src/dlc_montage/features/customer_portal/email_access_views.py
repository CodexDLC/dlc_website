"""Small, scanner-safe HTTP confirmation adapter for email access."""

import secrets

from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .email_access_services import end_email_access_session, sign_in_with_customer_email_access


def email_access_page(request, *, expired=False, status=200):
    """Serve a standalone page without third-party requests or referrer leakage."""
    nonce = secrets.token_urlsafe(24)
    response = render(
        request,
        "customer_portal/email_access.html",
        {"expired": expired, "script_nonce": nonce},
        status=status,
    )
    response["Cache-Control"] = "private, no-store"
    # Preserve the same-origin form's Origin/Referer for CSRF without cross-origin leakage.
    response["Referrer-Policy"] = "same-origin"
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response["Content-Security-Policy"] = (
        f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@never_cache
@sensitive_post_parameters("token")
@csrf_protect
@require_http_methods(["GET", "HEAD", "POST"])
def email_access(request):
    """GET only presents confirmation; only a CSRF-protected POST signs in."""
    if request.method == "POST":
        if request.POST.get("action") == "password_login":
            end_email_access_session(request)
            return redirect("account_login")
        destination = sign_in_with_customer_email_access(
            request=request,
            token=request.POST.get("token", ""),
            target=request.POST.get("target", ""),
        )
        if destination is None:
            return email_access_page(request, expired=True, status=410)
        response = redirect(destination)
        response["Referrer-Policy"] = "no-referrer"
        return response
    return email_access_page(request)
