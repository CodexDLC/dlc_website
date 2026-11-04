"""Read and validate customer email grants without changing their state."""

import hashlib
import re
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import CustomerEmailAccessGrant

EMAIL_ACCESS_SESSION_KEY = "customer_email_access_grant"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


def is_email_access_customer(user):
    """Reject staff, workers and privileged accounts, including later role changes."""
    return bool(
        user.is_active
        and not user.is_staff
        and not user.is_superuser
        and not hasattr(user, "employee")
        and not user.get_all_permissions()
    )


def grant_is_valid(grant, *, now=None):
    """Revalidate the original membership and the absolute issuance deadline."""
    membership = grant.membership
    return bool(
        grant.revoked_at is None
        and (now or timezone.now()) < grant.expires_at
        and membership.is_active
        and membership.client.is_active
        and membership.client_id == grant.client_id
        and membership.updated_at == grant.membership_updated_at
        and is_email_access_customer(membership.user)
    )


def grant_queryset():
    """Load the authorization relationships used on every access check."""
    return CustomerEmailAccessGrant.objects.select_related("membership__user", "membership__client")


@sensitive_variables()
def grant_for_token(token):
    """Return a live grant for a bounded, random bearer secret."""
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        return None
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    grant = grant_queryset().filter(token_digest=digest).first()
    return grant if grant is not None and grant_is_valid(grant) else None


def grant_for_session(*, grant_id, user_id):
    """Do not accept a session marker belonging to another account."""
    if type(grant_id) is not int or not 0 < grant_id < 2**63:
        return None
    grant = grant_queryset().filter(pk=grant_id, membership__user_id=user_id).first()
    return grant if grant is not None and grant_is_valid(grant) else None


def email_access_target(grant, target):
    """Resolve a closed target list; caller input is never a redirect URL."""
    if target == "works":
        day = grant.work_date.isoformat()
        return reverse("customer_portal:works") + "?" + urlencode({"from": day, "to": day})
    if target == "reviews":
        return reverse("customer_portal:reviews") + "?status=submitted"
    return None
