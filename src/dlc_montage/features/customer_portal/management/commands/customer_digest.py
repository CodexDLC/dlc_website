"""Safe preview, SMTP authentication check and idempotent one-shot digest delivery."""

from datetime import date
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.utils import timezone, translation

from features.customer_portal.digest_email import DigestSMTPAdapter, render_digest
from features.customer_portal.digest_selectors import customer_digest, scheduled_work_date
from features.customer_portal.digest_services import digest_actors, digest_config, send_customer_digest


class Command(BaseCommand):
    help = "Preview (without tokens), check SMTP or send one customer digest. Default: preview."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--send", action="store_true")
        group.add_argument("--scheduled", action="store_true")
        group.add_argument("--check-smtp", action="store_true")
        parser.add_argument("--work-date", type=date.fromisoformat)
        parser.add_argument("--output", help="Optional HTML preview path; never contains bearer tokens.")

    def handle(self, *args, **options):
        try:
            config = digest_config()
            adapter = DigestSMTPAdapter(config)
            if options["scheduled"] and options["work_date"]:
                raise CommandError("scheduled_date_override_forbidden")
            work_date = options["work_date"] or scheduled_work_date(timezone.now())
            if options["check_smtp"]:
                if not config.smtp_password:
                    self.stdout.write("skipped_password_missing")
                    return
                try:
                    success = adapter.check()
                except Exception:
                    raise CommandError("smtp_check_failed") from None
                self.stdout.write("smtp_ready" if success else "smtp_check_failed")
                return
            if work_date is None:
                self.stdout.write("not_due")
                return
            if options["send"] or options["scheduled"]:
                result = send_customer_digest(config=config, work_date=work_date, adapter=adapter)
                self.stdout.write(result)
                if result in {"failed", "uncertain"}:
                    raise CommandError("delivery_requires_operator_review")
                return
            _, recipient = digest_actors(config)
            digest = customer_digest(recipient=recipient, work_date=work_date)
            with translation.override("de"):
                rendered = render_digest(
                    digest=digest,
                    works_url=config.base_url + reverse("customer_portal:works")
                        + f"?from={work_date.isoformat()}&to={work_date.isoformat()}",
                    reviews_url=config.base_url + reverse("customer_portal:reviews") + "?status=submitted",
                )
            if options["output"]:
                Path(options["output"]).write_text(rendered.html, encoding="utf-8")
            self.stdout.write(rendered.text)
        except ValidationError:
            raise CommandError("customer_digest_configuration_or_data_invalid") from None
