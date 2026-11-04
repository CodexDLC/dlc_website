"""Validate explicit customer scope and durably claim one outbound digest attempt."""

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone, translation
from django.views.decorators.debug import sensitive_variables
from loguru import logger

from features.internal_time.policies import is_manager

from .digest_selectors import customer_digest
from .email_access_selectors import is_email_access_customer
from .email_access_services import issue_customer_email_access
from .models import ClientMembership, CustomerDigestDelivery

TEST_EMAIL = "primecodex@gmail.com"


@dataclass(frozen=True)
class DigestConfig:
    actor_id: int
    recipient_id: int
    client_id: int
    recipient_email: str = field(repr=False)
    from_email: str = field(repr=False)
    base_url: str
    mode: str
    smtp_host: str
    smtp_port: int
    smtp_user: str = field(repr=False)
    smtp_password: str = field(repr=False)
    smtp_timeout: int

    @property
    def delivery_email(self):
        return TEST_EMAIL if self.mode == "test" else self.recipient_email

    @property
    def cc(self):
        # A test envelope must never escape the explicitly approved test address.
        return () if self.mode == "test" or self.from_email.casefold() == self.delivery_email.casefold() else (
            self.from_email,
        )


@sensitive_variables()
def digest_config():
    """Require explicit IDs and mailbox; never infer authorization from email alone."""
    try:
        config = DigestConfig(
            actor_id=int(settings.CUSTOMER_DIGEST_ACTOR_ID),
            recipient_id=int(settings.CUSTOMER_DIGEST_RECIPIENT_USER_ID),
            client_id=int(settings.CUSTOMER_DIGEST_CLIENT_ID),
            recipient_email=settings.CUSTOMER_DIGEST_RECIPIENT_EMAIL.strip(),
            from_email=settings.CUSTOMER_DIGEST_FROM_EMAIL.strip(),
            base_url=settings.CUSTOMER_DIGEST_BASE_URL.rstrip("/"), mode=settings.CUSTOMER_DIGEST_MODE,
            smtp_host=settings.CUSTOMER_DIGEST_SMTP_HOST, smtp_port=int(settings.CUSTOMER_DIGEST_SMTP_PORT),
            smtp_user=settings.CUSTOMER_DIGEST_SMTP_USER,
            smtp_password=settings.CUSTOMER_DIGEST_SMTP_PASSWORD,
            smtp_timeout=int(settings.CUSTOMER_DIGEST_SMTP_TIMEOUT),
        )
        validate_email(config.recipient_email)
        validate_email(config.from_email)
        origin = urlsplit(config.base_url)
        if (config.mode not in {"test", "live"} or origin.scheme != "https" or not origin.hostname
                or origin.username or origin.password or origin.query or origin.fragment or origin.path
                or min(config.actor_id, config.recipient_id, config.client_id) < 1
                or not config.smtp_host or not config.smtp_user or not 1 <= config.smtp_port <= 65535
                or not 1 <= config.smtp_timeout <= 120):
            raise ValueError
    except (ValueError, TypeError, ValidationError) as exc:
        raise ValidationError("customer_digest_configuration_invalid") from exc
    return config


def digest_actors(config):
    """Recheck live membership and pure customer permissions before every operation."""
    actor = get_user_model().objects.filter(pk=config.actor_id).first()
    membership = ClientMembership.objects.select_related("user", "client").filter(
        user_id=config.recipient_id, client_id=config.client_id, is_active=True, client__is_active=True,
    ).first()
    if (actor is None or not is_manager(actor) or membership is None
            or not is_email_access_customer(membership.user)
            or membership.user.email.casefold() != config.recipient_email.casefold()):
        raise ValidationError("customer_digest_recipient_invalid")
    return actor, membership.user


@sensitive_variables()
def send_customer_digest(*, config, work_date, adapter):
    """Never retry a claimed date automatically, including interrupted/ambiguous SMTP."""
    if not config.smtp_password:
        logger.info("customer_digest_skipped", reason="smtp_password_missing")
        return "skipped_password_missing"
    actor, recipient = digest_actors(config)
    digest = customer_digest(recipient=recipient, work_date=work_date)
    # Commit the claim before issuing links or crossing the network boundary.
    try:
        with transaction.atomic():
            delivery = CustomerDigestDelivery.objects.create(
                recipient=recipient, client_id=config.client_id, work_date=work_date, mode=config.mode,
            )
    except IntegrityError:
        return "already_claimed"
    logger.bind(delivery_id=delivery.pk).info("customer_digest_started")
    try:
        # Authenticate transport first; a failed connection must not invalidate existing access.
        if not adapter.check():
            raise OSError("smtp_unavailable")
        # Bind issuance to the same explicit client under the membership lock.
        with transaction.atomic():
            ClientMembership.objects.select_for_update().get(user_id=recipient.pk)
            actor, recipient = digest_actors(config)
            with translation.override("de"):
                access = issue_customer_email_access(
                    actor=actor, recipient_user_id=recipient.pk,
                    recipient_email=config.recipient_email, work_date=work_date,
                )
            CustomerDigestDelivery.objects.filter(pk=delivery.pk).update(grant_id=access.grant_id)
    except Exception:
        CustomerDigestDelivery.objects.filter(pk=delivery.pk).update(status="failed", failure_code="preparation_failed")
        logger.bind(delivery_id=delivery.pk).warning("customer_digest_preparation_failed")
        return "failed"
    # Once this transition commits, every exception is ambiguous: SMTP may have accepted DATA.
    CustomerDigestDelivery.objects.filter(pk=delivery.pk).update(status="sending", attempted_at=timezone.now())
    try:
        sent = adapter.send_digest(
            digest=digest, works_url=config.base_url + access.works_url,
            reviews_url=config.base_url + access.reviews_url,
        )
        if sent != 1:
            raise OSError("smtp_acceptance_unknown")
    except Exception:
        CustomerDigestDelivery.objects.filter(pk=delivery.pk).update(status="uncertain", failure_code="smtp_uncertain")
        logger.bind(delivery_id=delivery.pk).warning("customer_digest_delivery_uncertain")
        return "uncertain"
    CustomerDigestDelivery.objects.filter(pk=delivery.pk).update(status="sent", sent_at=timezone.now())
    logger.bind(delivery_id=delivery.pk, site_count=len(digest.sites)).info("customer_digest_sent")
    return "sent"
