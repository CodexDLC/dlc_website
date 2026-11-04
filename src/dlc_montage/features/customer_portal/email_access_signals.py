"""A successful ordinary login replaces any earlier temporary authentication."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .email_access_selectors import EMAIL_ACCESS_SESSION_KEY


@receiver(user_logged_in, dispatch_uid="customer_portal.clear_email_access_on_login")
def clear_email_access_on_login(sender, request, user, **kwargs):
    """Magic sign-in sets its marker after login; all other logins stay ordinary."""
    if request is not None and EMAIL_ACCESS_SESSION_KEY in request.session:
        request.session.pop(EMAIL_ACCESS_SESSION_KEY, None)
        request.session.set_expiry(None)
