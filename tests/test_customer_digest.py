"""Customer digest scope, safe transport envelope and durable delivery boundaries."""

from dataclasses import replace
from datetime import date, datetime
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client as HttpClient
from django.utils import translation
from features.customer_portal.digest_email import DigestSMTPAdapter, render_digest
from features.customer_portal.digest_selectors import customer_digest, scheduled_work_date
from features.customer_portal.digest_services import digest_config, send_customer_digest
from features.customer_portal.models import (
    ClientMembership,
    CustomerDigestDelivery,
    CustomerEmailAccessGrant,
    SiteReview,
)
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.project_media.models import SitePhoto
from features.projects.models import AcObject, Client, ProjectGroup

pytestmark = pytest.mark.django_db
DAY = date(2026, 10, 27)


@pytest.fixture
def digest_setup(settings):
    manager = get_user_model().objects.create_superuser(username="digest-manager", password=None)
    customer = get_user_model().objects.create_user(username="digest-customer", email="customer@example.test")
    client = Client.objects.create(name="Digest client")
    ClientMembership.objects.create(user=customer, client=client, granted_by=manager)
    group = ProjectGroup.objects.create(name="Digest Anlage", client=client)
    site = AcObject.objects.create(group=group, name="J28", address="Teststraße 28")
    settings.CUSTOMER_DIGEST_ACTOR_ID = str(manager.pk)
    settings.CUSTOMER_DIGEST_RECIPIENT_USER_ID = str(customer.pk)
    settings.CUSTOMER_DIGEST_CLIENT_ID = str(client.pk)
    settings.CUSTOMER_DIGEST_RECIPIENT_EMAIL = customer.email
    settings.CUSTOMER_DIGEST_BASE_URL = "https://crm.example.test"
    settings.CUSTOMER_DIGEST_MODE = "test"
    settings.CUSTOMER_DIGEST_SMTP_PASSWORD = "test-only-password"  # noqa: S105
    settings.CUSTOMER_DIGEST_FROM_EMAIL = "sender@example.test"
    return manager, customer, site, digest_config()


class Transport:
    def __init__(self, *, fail_check=False, fail_send=False):
        self.fail_check, self.fail_send = fail_check, fail_send
        self.calls = []

    def check(self):
        if self.fail_check:
            raise OSError("private smtp exception")
        return True

    def send_digest(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_send:
            raise OSError("private smtp exception")
        return 1


@pytest.mark.parametrize(("utc", "expected"), [
    ("2026-10-26T07:00:00+00:00", date(2026, 10, 23)),
    ("2026-10-27T07:00:00+00:00", date(2026, 10, 26)),
    ("2026-10-23T06:00:00+00:00", date(2026, 10, 22)),
    ("2026-10-26T06:59:59+00:00", None),
    ("2026-10-24T12:00:00+00:00", None),
    ("2026-03-30T06:00:00+00:00", date(2026, 3, 27)),
])
def test_schedule_berlin_weekdays_and_dst(utc, expected):
    assert scheduled_work_date(datetime.fromisoformat(utc)) == expected


def test_missing_password_never_claims_or_issues(digest_setup):
    config = replace(digest_setup[3], smtp_password="")
    transport = Transport(fail_check=True)
    assert send_customer_digest(config=config, work_date=DAY, adapter=transport) == "skipped_password_missing"
    assert not CustomerDigestDelivery.objects.exists()
    assert not CustomerEmailAccessGrant.objects.exists()
    assert transport.calls == []


def test_success_durable_idempotence_and_links_not_persisted(digest_setup):
    config = digest_setup[3]
    transport = Transport()
    assert send_customer_digest(config=config, work_date=DAY, adapter=transport) == "sent"
    delivery = CustomerDigestDelivery.objects.get()
    assert delivery.status == "sent" and delivery.sent_at and delivery.attempted_at and delivery.grant_id
    assert send_customer_digest(config=config, work_date=DAY, adapter=transport) == "already_claimed"
    assert len(transport.calls) == 1
    assert CustomerEmailAccessGrant.objects.count() == 1
    assert "#token=" in transport.calls[0]["works_url"]
    token = transport.calls[0]["works_url"].split("#token=")[1].split("&")[0]
    assert token not in str(vars(delivery))
    assert token not in str(vars(CustomerEmailAccessGrant.objects.get()))
    assert token not in repr(config)


def test_german_email_links_and_confirmation_destinations_preserve_callers_language(digest_setup):
    transport = Transport()
    with translation.override("ru"):
        assert send_customer_digest(config=digest_setup[3], work_date=DAY, adapter=transport) == "sent"
        assert translation.get_language() == "ru"
    for key, target in (("works_url", "works"), ("reviews_url", "reviews")):
        parsed = urlsplit(transport.calls[0][key])
        assert parsed.path.startswith("/de/cabinet/customer/")
        values = {key: value[0] for key, value in parse_qs(parsed.fragment).items()}
        response = HttpClient().post(parsed.path, values)
        assert response.status_code == 302
        assert response.url.startswith(f"/de/cabinet/customer/{target}/")
        assert ("from=2026-10-27&to=2026-10-27" if target == "works" else "status=submitted") in response.url


@pytest.mark.parametrize(("fail_check", "fail_send", "status"), [(True, False, "failed"), (False, True, "uncertain")])
def test_failures_never_auto_resend_or_expose_smtp_errors(digest_setup, fail_check, fail_send, status):
    config = digest_setup[3]
    transport = Transport(fail_check=fail_check, fail_send=fail_send)
    assert send_customer_digest(config=config, work_date=DAY, adapter=transport) == status
    row = CustomerDigestDelivery.objects.get()
    assert row.status == status and row.sent_at is None
    assert "private" not in row.failure_code
    assert send_customer_digest(config=config, work_date=DAY, adapter=Transport()) == "already_claimed"
    assert CustomerEmailAccessGrant.objects.count() == (0 if fail_check else 1)


@pytest.mark.parametrize("state", ["preparing", "sending", "uncertain", "failed", "sent"])
def test_interrupted_or_terminal_claim_is_never_retried(digest_setup, state):
    _, customer, site, config = digest_setup
    CustomerDigestDelivery.objects.create(
        recipient=customer, client=site.group.client, work_date=DAY, mode="test", status=state,
    )
    transport = Transport()
    assert send_customer_digest(config=config, work_date=DAY, adapter=transport) == "already_claimed"
    assert transport.calls == []
    assert not CustomerEmailAccessGrant.objects.exists()


@pytest.mark.parametrize("change", ["email", "client", "staff", "inactive", "manager"])
def test_explicit_scope_is_validated_before_claim(digest_setup, change):
    _manager, customer, _, config = digest_setup
    if change == "email":
        config = replace(config, recipient_email="somebody@example.test")
    elif change == "client":
        config = replace(config, client_id=99999)
    elif change == "staff":
        customer.is_staff = True
        customer.save()
    elif change == "inactive":
        customer.is_active = False
        customer.save()
    else:
        config = replace(config, actor_id=customer.pk)
    with pytest.raises(ValidationError):
        send_customer_digest(config=config, work_date=DAY, adapter=Transport())
    assert not CustomerDigestDelivery.objects.exists()


def add_photo(site, index, source="nextcloud"):
    return SitePhoto.objects.create(
        site=site, source_id=str(index), source_kind=source, checksum="abc", image=f"test/{index}.jpg",
        original_name="photo.jpg", content_type="image/jpeg", size=1,
    )


def test_photo_count_includes_nextcloud_uploads_once_but_no_history_or_other_client(digest_setup):
    _, customer, site, _ = digest_setup
    SiteReview.objects.create(site=site, status="submitted")
    add_photo(site, 1)
    add_photo(site, 2, "upload")
    no_photo = AcObject.objects.create(group=site.group, name="No photo")
    SiteReview.objects.create(site=no_photo, status="submitted")
    accepted = AcObject.objects.create(group=site.group, name="Accepted")
    SiteReview.objects.create(site=accepted, status="accepted")
    add_photo(accepted, 3)
    other = AcObject.objects.create(group=ProjectGroup.objects.create(
        name="Other", client=Client.objects.create(name="Other")), name="Other customer")
    SiteReview.objects.create(site=other, status="submitted")
    add_photo(other, 4)
    assert customer_digest(recipient=customer, work_date=DAY).pending_photo_count == 1


def test_accepted_current_snapshot_intervals_plan_counts_and_compact_body(digest_setup, monkeypatch):
    from types import SimpleNamespace

    manager, customer, site, _config = digest_setup
    report = MbgDailyReport.objects.create(author=manager, site=site, work_date=DAY, status="accepted")
    MbgReportRevision.objects.create(report=report, actor=manager, version=1, action="accept", snapshot={
        "status": "accepted", "entries": [
            {"description": "DO NOT SHOW WORK", "start": "08:00:00", "end": "10:00:00", "unit": "piece"},
            {"description": "Cleanup", "start": "10:00:00", "end": "11:00:00", "internal_only": True,
             "work_type_code": "freiraeumen"},
            {"description": "Pause", "start": "11:00:00", "end": "12:00:00", "is_break": True},
        ],
    })
    monkeypatch.setattr("features.customer_portal.digest_selectors.site_work_plan", lambda site, **kwargs:
        SimpleNamespace(rows=[
            SimpleNamespace(item=SimpleNamespace(is_required=True), is_completed=True),
            SimpleNamespace(item=SimpleNamespace(is_required=True), is_completed=False),
            SimpleNamespace(item=SimpleNamespace(is_required=False), is_completed=True),
        ]))
    digest = customer_digest(recipient=customer, work_date=DAY)
    assert digest.sites[0].intervals == "08:00–11:00"  # noqa: RUF001
    assert (digest.sites[0].completed, digest.sites[0].planned) == (1, 2)
    rendered = render_digest(digest=digest, works_url="https://example.test/works", reviews_url="https://example.test/reviews")
    assert "DO NOT SHOW WORK" not in rendered.html
    assert "Cleanup" not in rendered.html
    assert "1/2" in rendered.html and "08:00–11:00" in rendered.html  # noqa: RUF001
    assert rendered.html.count('<h2 ') == 2
    report.version = 2
    report.save()
    with pytest.raises(ValidationError):
        customer_digest(recipient=customer, work_date=DAY)


def test_preview_is_read_only_and_contains_no_bearer(digest_setup, tmp_path):
    output = StringIO()
    preview = tmp_path / "preview.html"
    with translation.override("ru"):
        call_command("customer_digest", work_date=DAY, output=str(preview), stdout=output)
        assert translation.get_language() == "ru"
    assert "#token=" not in preview.read_text(encoding="utf-8")
    assert "?from=2026-10-27&to=2026-10-27" in output.getvalue()
    assert "https://crm.example.test/de/cabinet/customer/works/" in output.getvalue()
    assert "https://crm.example.test/de/cabinet/customer/reviews/" in output.getvalue()
    assert not CustomerDigestDelivery.objects.exists()
    assert not CustomerEmailAccessGrant.objects.exists()


def test_transport_uses_only_approved_test_envelope_and_live_copies_sender(digest_setup, monkeypatch):
    from django.core.mail.backends.locmem import EmailBackend

    config = digest_setup[3]
    monkeypatch.setattr(DigestSMTPAdapter, "_connection", lambda self: EmailBackend())
    import django.core.mail
    rendered = render_digest(digest=customer_digest(recipient=digest_setup[1], work_date=DAY),
                             works_url="https://example.test/works", reviews_url="https://example.test/reviews")
    assert DigestSMTPAdapter(config).send(rendered) == 1
    message = django.core.mail.outbox[-1]
    assert message.recipients() == ["primecodex@gmail.com"] and message.cc == []
    assert message.alternatives[0].mimetype == "text/html"
    assert DigestSMTPAdapter(replace(config, mode="live")).send(rendered) == 1
    assert django.core.mail.outbox[-1].recipients() == [config.recipient_email, config.from_email]


def test_runner_env_is_literal_allowlisted_and_password_removal_clears_stale_value(tmp_path):
    path = Path(__file__).parents[1] / "deploy/customer-digest/run.py"
    spec = spec_from_file_location("digest_runner", path)
    runner = module_from_spec(spec)
    spec.loader.exec_module(runner)
    environment = tmp_path / "mail.env"
    environment.write_text('SECRET_KEY=do-not-copy\nCUSTOMER_DIGEST_MODE=test\n'
                           'CUSTOMER_DIGEST_SMTP_PASSWORD="literal$(no-shell)"\n', encoding="utf-8")
    data = runner.read_mail_environment(environment)
    assert "SECRET_KEY" not in data and "literal$(no-shell)" in data
    environment.write_text("CUSTOMER_DIGEST_MODE=test\n", encoding="utf-8")
    assert "CUSTOMER_DIGEST_SMTP_PASSWORD=\n" in runner.read_mail_environment(environment)
