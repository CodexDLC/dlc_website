"""Atomic issuance and explicit sign-in for customer email access."""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib.auth import login, logout
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from features.internal_time.policies import is_manager

from .email_access_selectors import (
    EMAIL_ACCESS_SESSION_KEY,
    email_access_target,
    grant_for_token,
    grant_is_valid,
    grant_queryset,
    is_email_access_customer,
)
from .models import ClientMembership, CustomerEmailAccessGrant


@dataclass(frozen=True)
class IssuedCustomerEmailAccess:
    """Transient delivery material; repr intentionally excludes bearer links."""

    grant_id: int
    works_url: str = field(repr=False)
    reviews_url: str = field(repr=False)


@transaction.atomic
@sensitive_variables()
def issue_customer_email_access(*, actor, recipient_user_id, recipient_email, work_date):
    """Replace both links and all magic sessions for one explicitly selected customer.

    Return relative fragment-only URLs for an HTTPS mail adapter to prefix with its
    configured public origin. Never print or persist the returned delivery object.
    This service sends no email and never creates or infers a membership.
    """
    if not is_manager(actor):
        raise PermissionDenied
    if type(work_date) is not date:
        raise ValidationError("Ein gültiges Arbeitsdatum ist erforderlich.")
    membership = (
        ClientMembership.objects.select_for_update()
        .select_related("user", "client")
        .filter(user_id=recipient_user_id, is_active=True, client__is_active=True)
        .first()
    )
    if (
        membership is None
        or not is_email_access_customer(membership.user)
        or not recipient_email
        or membership.user.email.casefold() != recipient_email.strip().casefold()
    ):
        raise ValidationError("Kein gültiger Kundenzugang für diesen Empfänger.")
    now = timezone.now()
    CustomerEmailAccessGrant.objects.filter(membership=membership, revoked_at__isnull=True).update(revoked_at=now)
    token = secrets.token_urlsafe(32)
    grant = CustomerEmailAccessGrant.objects.create(
        membership=membership,
        client=membership.client,
        membership_updated_at=membership.updated_at,
        token_digest=hashlib.sha256(token.encode("ascii")).hexdigest(),
        work_date=work_date,
        issued_by=actor,
        expires_at=now + timedelta(hours=24),
    )
    entry = reverse("customer_portal:email_access")
    return IssuedCustomerEmailAccess(
        grant_id=grant.pk,
        works_url=entry + "#" + urlencode({"token": token, "target": "works"}),
        reviews_url=entry + "#" + urlencode({"token": token, "target": "reviews"}),
    )


@transaction.atomic
@sensitive_variables()
def sign_in_with_customer_email_access(*, request, token, target):
    """Explicit POST sign-in; the issuance deadline never moves forward."""
    candidate = grant_for_token(token)
    if candidate is None:
        return None
    # Use the same lock order as issuance, so a concurrent replacement wins safely.
    if not ClientMembership.objects.select_for_update().filter(pk=candidate.membership_id).exists():
        return None
    grant = grant_queryset().filter(pk=candidate.pk).first()
    if grant is None:
        return None
    destination = email_access_target(grant, target)
    if destination is None or not grant_is_valid(grant):
        return None
    # Explicit confirmation authorizes the switch; flush any prior privileged session.
    logout(request)
    login(request, grant.membership.user, backend="django.contrib.auth.backends.ModelBackend")
    request.session[EMAIL_ACCESS_SESSION_KEY] = grant.pk
    request.session.set_expiry(grant.expires_at)
    return destination


@transaction.atomic
def revoke_customer_email_access(*, actor, recipient_user_id):
    """Immediately revoke all links and magic sessions for one customer."""
    if not is_manager(actor):
        raise PermissionDenied
    membership = ClientMembership.objects.select_for_update().filter(user_id=recipient_user_id).first()
    if membership is not None:
        CustomerEmailAccessGrant.objects.filter(membership=membership, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )


def end_email_access_session(request):
    """Explicitly leave temporary authentication before the regular login form."""
    logout(request)
