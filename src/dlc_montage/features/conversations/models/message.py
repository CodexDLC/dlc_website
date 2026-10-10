import secrets
from typing import ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    class Source(models.TextChoices):
        CONTACT_FORM = "contact_form", _("Contact Form")
        EMAIL_IMPORT = "email_import", _("Email Import")
        MANUAL = "manual", _("Manual")

    class Channel(models.TextChoices):
        EMAIL = "email", _("Email")
        WHATSAPP = "whatsapp", _("WhatsApp")
        TELEGRAM = "telegram", _("Telegram")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        PROCESSED = "processed", _("Processed")
        SPAM = "spam", _("Spam")

    class Topic(models.TextChoices):
        GENERAL = "general", _("General Inquiry")
        SUPPORT = "support", _("Support")
        FEEDBACK = "feedback", _("Feedback")
        OTHER = "other", _("Other")

    # ── Sender ───────────────────────────────────────────────────────────────
    sender_name = models.CharField(_("sender name"), max_length=255)
    sender_email = models.EmailField(_("sender email"))
    sender_phone = models.CharField(_("sender phone"), max_length=50, blank=True)

    # ── Content ──────────────────────────────────────────────────────────────
    subject = models.CharField(_("subject"), max_length=500, blank=True)
    body = models.TextField(_("body"))

    # ── Classification ───────────────────────────────────────────────────────
    topic = models.CharField(_("topic"), max_length=30, choices=Topic.choices, default=Topic.GENERAL, db_index=True)
    status = models.CharField(_("status"), max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    source = models.CharField(
        _("source"), max_length=20, choices=Source.choices, default=Source.CONTACT_FORM, db_index=True
    )
    channel = models.CharField(
        _("channel"), max_length=20, choices=Channel.choices, default=Channel.EMAIL, db_index=True
    )
    is_read = models.BooleanField(_("read"), default=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)

    # ── Threading ────────────────────────────────────────────────────────────
    # Unique opaque token embedded in reply-to email headers.
    # Lets the email import service link inbound replies to this thread.
    thread_key = models.CharField(
        _("thread key"),
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering: ClassVar[list[str]] = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.thread_key:
            self.thread_key = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    def __str__(self):
        preview = self.subject or self.body[:60]
        return f"[{self.get_status_display()}] {self.sender_name} — {preview}"
