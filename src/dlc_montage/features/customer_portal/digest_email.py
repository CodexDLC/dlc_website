"""HTML presentation and the dedicated TLS SMTP adapter for customer digests."""

from dataclasses import dataclass, field

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string


@dataclass(frozen=True)
class RenderedDigest:
    subject: str
    text: str = field(repr=False)
    html: str = field(repr=False)


def render_digest(*, digest, works_url, reviews_url):
    context = {"digest": digest, "works_url": works_url, "reviews_url": reviews_url}
    return RenderedDigest(
        subject=f"DLC Montage · Tagesübersicht {digest.work_date:%d.%m.%Y}",
        text=render_to_string("customer_portal/email/digest.txt", context),
        html=render_to_string("customer_portal/email/digest.html", context),
    )


class DigestSMTPAdapter:
    """Explicit Gmail-compatible STARTTLS transport, without application-mail fallback."""

    def __init__(self, config):
        self.config = config

    def _connection(self):
        return EmailBackend(
            host=self.config.smtp_host, port=self.config.smtp_port, username=self.config.smtp_user,
            password=self.config.smtp_password, use_tls=True, use_ssl=False,
            timeout=self.config.smtp_timeout, fail_silently=False,
        )

    def check(self):
        with self._connection() as connection:
            return connection.connection is not None

    def send(self, rendered):
        with self._connection() as connection:
            message = EmailMultiAlternatives(
                subject=rendered.subject, body=rendered.text, from_email=self.config.from_email,
                to=[self.config.delivery_email], cc=list(self.config.cc), connection=connection,
            )
            message.attach_alternative(rendered.html, "text/html")
            return message.send(fail_silently=False)

    def send_digest(self, *, digest, works_url, reviews_url):
        return self.send(render_digest(digest=digest, works_url=works_url, reviews_url=reviews_url))
