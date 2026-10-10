from typing import ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Message


class ContactForm(forms.ModelForm):
    class Meta:
        model = Message
        fields: ClassVar[list[str]] = ["sender_name", "sender_email", "sender_phone", "subject", "topic", "body"]
        labels: ClassVar[dict[str, str]] = {
            "sender_name": _("Your Name"),
            "sender_email": _("Your Email"),
            "sender_phone": _("Phone (optional)"),
            "subject": _("Subject"),
            "topic": _("Topic"),
            "body": _("Message"),
        }
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "body": forms.Textarea(attrs={"rows": 5}),
            "sender_phone": forms.TextInput(attrs={"placeholder": _("+49 …")}),
        }
