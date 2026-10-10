from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .message import Message


class MessageReply(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name=_("message"),
    )
    body = models.TextField(_("body"))
    sent_at = models.DateTimeField(_("sent at"), auto_now_add=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_replies",
        verbose_name=_("sent by"),
    )
    # True = inbound reply received from sender via email import
    is_inbound = models.BooleanField(_("inbound"), default=False)

    class Meta:
        verbose_name = _("Reply")
        verbose_name_plural = _("Replies")
        ordering: ClassVar[list[str]] = ["sent_at"]

    def __str__(self):
        direction = "←" if self.is_inbound else "→"
        return f"{direction} {self.message.sender_email} @ {self.sent_at:%Y-%m-%d %H:%M}"
