"""Security contracts of customer email links and their resulting sessions."""

import hashlib
import re
from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client as HttpClient
from django.urls import reverse
from django.utils import timezone
from features.customer_portal.email_access_selectors import (
    EMAIL_ACCESS_SESSION_KEY,
    grant_for_token,
)
from features.customer_portal.email_access_services import (
    issue_customer_email_access,
    revoke_customer_email_access,
)
from features.customer_portal.models import ClientMembership, CustomerEmailAccessGrant, SiteReview
from features.projects.models import AcObject, Client, ProjectGroup
from features.staff.models import Employee

pytestmark = pytest.mark.django_db
DAY = date(2026, 10, 23)


@pytest.fixture
def access_actors():
    users = get_user_model()
    manager = users.objects.create_superuser(username="access-manager", email="manager@example.test", password=None)
    customer = users.objects.create_user(username="access-customer", email="customer@example.test", password="ordinary")
    other = users.objects.create_user(username="access-other", email="other@example.test")
    client_a = Client.objects.create(name="Access A")
    client_b = Client.objects.create(name="Access B")
    membership = ClientMembership.objects.create(user=customer, client=client_a, granted_by=manager)
    ClientMembership.objects.create(user=other, client=client_b, granted_by=manager)
    site_a = AcObject.objects.create(
        group=ProjectGroup.objects.create(name="Access Anlage A", client=client_a), name="A"
    )
    site_b = AcObject.objects.create(
        group=ProjectGroup.objects.create(name="Access Anlage B", client=client_b), name="B"
    )
    return manager, customer, other, membership, site_a, site_b


def issue(actors):
    manager, customer, *_ = actors
    return issue_customer_email_access(
        actor=manager, recipient_user_id=customer.pk, recipient_email=customer.email, work_date=DAY
    )


def link_data(url):
    parsed = urlsplit(url)
    data = {key: value[0] for key, value in parse_qs(parsed.fragment).items()}
    return parsed.path, data


def confirm(browser, url):
    path, data = link_data(url)
    return browser.post(path, data)


def test_one_issuance_has_two_targets_one_hashed_secret_and_absolute_deadline(access_actors):
    before = timezone.now()
    issued = issue(access_actors)
    after = timezone.now()
    path, works = link_data(issued.works_url)
    _, reviews = link_data(issued.reviews_url)
    assert urlsplit(issued.works_url).query == ""
    assert urlsplit(issued.reviews_url).query == ""
    assert works["token"] == reviews["token"]
    assert works["target"] == "works" and reviews["target"] == "reviews"
    grant = CustomerEmailAccessGrant.objects.get(pk=issued.grant_id)
    assert grant.token_digest == hashlib.sha256(works["token"].encode()).hexdigest()
    assert works["token"] not in repr(issued)
    assert works["token"] not in str(vars(grant))
    assert before + timedelta(hours=24) <= grant.expires_at <= after + timedelta(hours=24)
    for url, expected in (
        (issued.works_url, reverse("customer_portal:works") + "?from=2026-10-23&to=2026-10-23"),
        (issued.reviews_url, reverse("customer_portal:reviews") + "?status=submitted"),
    ):
        browser = HttpClient()
        response = confirm(browser, url)
        assert response.status_code == 302
        assert response.url == expected
        assert browser.session[SESSION_KEY] == str(access_actors[1].pk)
        assert browser.session[EMAIL_ACCESS_SESSION_KEY] == grant.pk
        assert browser.session.get_expiry_date() == grant.expires_at
        assert browser.get(expected).status_code == 200
    grant.refresh_from_db()
    assert grant.expires_at <= after + timedelta(hours=24)
    assert CustomerEmailAccessGrant.objects.count() == 1
    assert works["token"] not in path


@pytest.mark.parametrize("method", ["get", "head"])
def test_scanner_get_and_head_do_not_authenticate_or_consume(access_actors, method):
    issued = issue(access_actors)
    browser = HttpClient()
    path, data = link_data(issued.works_url)
    response = getattr(browser, method)(path)
    assert response.status_code == 200
    assert SESSION_KEY not in browser.session
    assert EMAIL_ACCESS_SESSION_KEY not in browser.session
    assert grant_for_token(data["token"]) is not None
    assert SiteReview.objects.count() == 0
    assert data["token"].encode() not in response.content
    assert "no-store" in response["Cache-Control"]
    assert response["Referrer-Policy"] == "same-origin"
    assert "default-src 'none'" in response["Content-Security-Policy"]
    assert "noindex" in response["X-Robots-Tag"]


def test_review_link_only_shows_pending_customer_reviews_and_default_keeps_history(access_actors):
    _, _, _, _, site_a, site_b = access_actors
    pending = SiteReview.objects.create(site=site_a, status="submitted")
    SiteReview.objects.create(site=site_b, status="submitted")
    accepted_site = AcObject.objects.create(group=site_a.group, name="Accepted")
    accepted = SiteReview.objects.create(site=accepted_site, status="accepted")
    browser = HttpClient()
    response = confirm(browser, issue(access_actors).reviews_url)
    assert response.url == reverse("customer_portal:reviews") + "?status=submitted"
    page = browser.get(response.url)
    assert list(page.context["reviews"]) == [pending]
    history = browser.get(reverse("customer_portal:reviews"))
    assert {review.pk for review in history.context["reviews"]} == {pending.pk, accepted.pk}
    assert list(SiteReview.objects.order_by("pk").values_list("status", flat=True)) == [
        "submitted",
        "submitted",
        "accepted",
    ]


def test_bearer_secret_never_appears_in_server_request_uri_logs_response_or_session(access_actors, caplog):
    issued = issue(access_actors)
    path, data = link_data(issued.works_url)
    browser = HttpClient()
    page = browser.get(path)
    response = browser.post(path, data)
    assert response.status_code == 302
    assert data["token"] not in response.wsgi_request.get_full_path()
    assert data["token"].encode() not in page.content + response.content
    assert data["token"] not in str(dict(browser.session))
    data["target"] = "invalid"
    assert browser.post(path, data).status_code == 410
    assert data["token"] not in caplog.text


def test_confirmation_requires_csrf_and_explicit_post(access_actors):
    issued = issue(access_actors)
    browser = HttpClient(enforce_csrf_checks=True)
    path, data = link_data(issued.works_url)
    response = browser.post(path, data)
    assert response.status_code == 403
    assert SESSION_KEY not in browser.session
    page = browser.get(path)
    assert b"window.location.hash" in page.content
    assert b"window.history.replaceState" in page.content
    assert b"disabled" in page.content
    data["csrfmiddlewaretoken"] = browser.cookies["csrftoken"].value
    assert browser.post(path, data).status_code == 302
    assert browser.session[SESSION_KEY] == str(access_actors[1].pk)


def test_confirmation_document_referrer_policy_matches_http_and_html(access_actors):
    browser = HttpClient()
    path, _ = link_data(issue(access_actors).works_url)
    for response in (browser.get(path, secure=True), browser.post(path, {}, secure=True)):
        assert response.status_code in {200, 410}
        assert response["Referrer-Policy"] == "same-origin"
        policies = re.findall(r'<meta name="referrer" content="([^"]+)">', response.content.decode())
        assert policies == [response["Referrer-Policy"]]


@pytest.mark.parametrize("target", ["works", "reviews"])
@pytest.mark.parametrize(("origin", "csrf", "expected"), [
    ("https://testserver", "valid", 302),
    (None, "valid", 302),
    ("null", "valid", 403),
    ("https://foreign.example", "valid", 403),
    ("https://testserver", "missing", 403),
    ("https://testserver", "invalid", 403),
])
def test_https_confirmation_preserves_csrf_and_origin_checks(access_actors, target, origin, csrf, expected):
    issued = issue(access_actors)
    path, data = link_data(getattr(issued, f"{target}_url"))
    browser = HttpClient(enforce_csrf_checks=True)
    assert browser.get(path, secure=True).status_code == 200
    if csrf != "missing":
        data["csrfmiddlewaretoken"] = browser.cookies["csrftoken"].value if csrf == "valid" else "a" * 64
    headers = {"HTTP_REFERER": f"https://testserver{path}"}
    if origin is not None:
        headers["HTTP_ORIGIN"] = origin
    response = browser.post(path, data, secure=True, **headers)
    assert response.status_code == expected
    if expected == 302:
        assert browser.session[SESSION_KEY] == str(access_actors[1].pk)
        assert response["Referrer-Policy"] == "no-referrer"
    else:
        assert SESSION_KEY not in browser.session
    assert SiteReview.objects.count() == 0


def test_new_issuance_revokes_both_old_links_and_every_old_magic_session(access_actors):
    first = issue(access_actors)
    browsers = [HttpClient(), HttpClient()]
    for browser, url in zip(browsers, [first.works_url, first.reviews_url], strict=True):
        assert confirm(browser, url).status_code == 302
    second = issue(access_actors)
    assert CustomerEmailAccessGrant.objects.get(pk=first.grant_id).revoked_at is not None
    for url in (first.works_url, first.reviews_url):
        assert confirm(HttpClient(), url).status_code == 410
    for browser in browsers:
        assert browser.get(reverse("customer_portal:works")).status_code == 410
        assert SESSION_KEY not in browser.session
    assert confirm(HttpClient(), second.works_url).status_code == 302
    assert confirm(HttpClient(), second.reviews_url).status_code == 302


def test_expiry_boundary_does_not_slide_on_repeated_confirmation(access_actors):
    issued = issue(access_actors)
    grant = CustomerEmailAccessGrant.objects.get(pk=issued.grant_id)
    original_expiry = grant.expires_at
    browser = HttpClient()
    assert confirm(browser, issued.works_url).status_code == 302
    assert confirm(browser, issued.reviews_url).status_code == 302
    grant.refresh_from_db()
    assert grant.expires_at == original_expiry
    assert browser.session.get_expiry_date() == original_expiry
    CustomerEmailAccessGrant.objects.filter(pk=grant.pk).update(expires_at=timezone.now())
    assert grant_for_token(link_data(issued.works_url)[1]["token"]) is None
    assert confirm(HttpClient(), issued.works_url).status_code == 410
    assert browser.get(reverse("customer_portal:works")).status_code == 410
    assert SESSION_KEY not in browser.session


def test_explicit_revocation_does_not_affect_password_session(access_actors):
    issued = issue(access_actors)
    magic = HttpClient()
    ordinary = HttpClient()
    assert ordinary.login(username=access_actors[1].username, password="ordinary")
    assert confirm(magic, issued.works_url).status_code == 302
    manager, customer, *_ = access_actors
    revoke_customer_email_access(actor=manager, recipient_user_id=customer.pk)
    assert magic.get(reverse("customer_portal:home")).status_code == 410
    assert ordinary.get(reverse("customer_portal:home")).status_code == 200
    assert EMAIL_ACCESS_SESSION_KEY not in ordinary.session
    issue(access_actors)
    assert ordinary.get(reverse("customer_portal:home")).status_code == 200


def test_same_customer_password_login_replaces_temporary_session(access_actors):
    from django.contrib.auth import authenticate, login
    from django.test import RequestFactory

    issued = issue(access_actors)
    browser = HttpClient()
    assert confirm(browser, issued.works_url).status_code == 302
    request = RequestFactory().post(reverse("account_login"))
    request.session = browser.session
    request.user = access_actors[1]
    user = authenticate(request, username=access_actors[1].username, password="ordinary")
    assert user is not None
    login(request, user)
    request.session.save()
    assert browser.session[SESSION_KEY] == str(access_actors[1].pk)
    assert EMAIL_ACCESS_SESSION_KEY not in browser.session
    assert "_session_expiry" not in browser.session
    revoke_customer_email_access(actor=access_actors[0], recipient_user_id=access_actors[1].pk)
    assert browser.get(reverse("customer_portal:home")).status_code == 200


def test_explicit_password_login_transition_uses_normal_http_flow(access_actors):
    issued = issue(access_actors)
    browser = HttpClient()
    assert confirm(browser, issued.works_url).status_code == 302
    response = browser.post(reverse("customer_portal:email_access"), {"action": "password_login"})
    assert response.status_code == 302
    assert response.url == reverse("account_login")
    assert SESSION_KEY not in browser.session
    response = browser.post(reverse("account_login"), {"login": access_actors[1].email, "password": "ordinary"})
    assert response.status_code == 302
    assert browser.session[SESSION_KEY] == str(access_actors[1].pk)
    assert EMAIL_ACCESS_SESSION_KEY not in browser.session
    revoke_customer_email_access(actor=access_actors[0], recipient_user_id=access_actors[1].pk)
    assert browser.get(reverse("customer_portal:home")).status_code == 200


@pytest.mark.parametrize(
    "target", ["https://evil.example/", "//evil.example/", "/admin/", "", "account", "works?next=/admin/"]
)
def test_closed_target_list_rejects_arbitrary_redirects_without_login(access_actors, target):
    issued = issue(access_actors)
    path, data = link_data(issued.works_url)
    data["target"] = target
    data["next"] = "https://evil.example/"
    browser = HttpClient()
    response = browser.post(path, data)
    assert response.status_code == 410
    assert "Location" not in response
    assert SESSION_KEY not in browser.session


@pytest.mark.parametrize("token", ["", "x", "x" * 43, "x" * 10000, "../invalid", "ä" * 43])
def test_invalid_secrets_fail_without_echo_or_exception(access_actors, token):
    issue(access_actors)
    browser = HttpClient()
    response = browser.post(reverse("customer_portal:email_access"), {"token": token, "target": "works"})
    assert response.status_code == 410
    assert SESSION_KEY not in browser.session
    if len(token) > 10:
        assert token.encode() not in response.content


def test_customer_scope_and_cross_account_confirmation_are_explicit(access_actors):
    manager, customer, _, _, site_a, site_b = access_actors
    issued = issue(access_actors)
    browser = HttpClient()
    browser.force_login(manager)
    page = browser.get(link_data(issued.works_url)[0])
    assert page.status_code == 200
    assert manager.username.encode() in page.content
    assert b"melden Sie dieses Konto ab" in page.content
    assert browser.session[SESSION_KEY] == str(manager.pk)
    path, data = link_data(issued.works_url)
    data["user_id"] = manager.pk
    data["client_id"] = site_b.group.client_id
    assert browser.post(path, data).status_code == 302
    assert browser.session[SESSION_KEY] == str(customer.pk)
    assert browser.get(reverse("customer_portal:site", args=[site_a.pk])).status_code == 200
    assert browser.get(reverse("customer_portal:site", args=[site_b.pk])).status_code == 404
    assert browser.post(reverse("customer_portal:review_decision", args=[site_b.pk]), {}).status_code == 404
    for name in ("customer_portal:memberships", "customer_portal:membership_edit", "cabinet:workspace_home"):
        assert browser.get(reverse(name)).status_code == 403
    assert browser.get(reverse("admin:index")).status_code == 403
    assert SiteReview.objects.count() == 0


@pytest.mark.parametrize(
    "change",
    [
        "staff",
        "superuser",
        "permission",
        "worker",
        "inactive_user",
        "inactive_membership",
        "inactive_client",
        "client_changed",
        "membership_updated",
    ],
)
def test_authorization_changes_invalidate_existing_links_and_sessions(access_actors, change):
    _manager, customer, _, membership, _, site_b = access_actors
    issued = issue(access_actors)
    browser = HttpClient()
    assert confirm(browser, issued.works_url).status_code == 302
    if change == "staff":
        get_user_model().objects.filter(pk=customer.pk).update(is_staff=True)
    elif change == "superuser":
        get_user_model().objects.filter(pk=customer.pk).update(is_superuser=True)
    elif change == "permission":
        customer.user_permissions.add(Permission.objects.get(codename="manage_reports"))
    elif change == "worker":
        Employee.objects.create(user=customer, first_name="Customer", last_name="Worker")
    elif change == "inactive_user":
        get_user_model().objects.filter(pk=customer.pk).update(is_active=False)
    elif change == "inactive_membership":
        ClientMembership.objects.filter(pk=membership.pk).update(is_active=False)
    elif change == "inactive_client":
        Client.objects.filter(pk=membership.client_id).update(is_active=False)
    elif change == "client_changed":
        ClientMembership.objects.filter(pk=membership.pk).update(client=site_b.group.client)
    elif change == "membership_updated":
        membership.can_manage_projects = True
        membership.save()
    assert confirm(HttpClient(), issued.works_url).status_code == 410
    assert browser.get(reverse("admin:index")).status_code == 410
    assert SESSION_KEY not in browser.session


@pytest.mark.parametrize(
    "change",
    [
        "staff",
        "superuser",
        "permission",
        "worker",
        "inactive_user",
        "inactive_membership",
        "inactive_client",
        "email",
        "no_membership",
    ],
)
def test_issuance_requires_existing_active_unprivileged_recipient(access_actors, change):
    manager, customer, _, membership, *_ = access_actors
    if change == "staff":
        customer.is_staff = True
        customer.save()
    elif change == "superuser":
        customer.is_superuser = True
        customer.save()
    elif change == "permission":
        customer.user_permissions.add(Permission.objects.get(codename="manage_reports"))
    elif change == "worker":
        Employee.objects.create(user=customer, first_name="C", last_name="W")
    elif change == "inactive_user":
        customer.is_active = False
        customer.save()
    elif change == "inactive_membership":
        membership.is_active = False
        membership.save()
    elif change == "inactive_client":
        membership.client.is_active = False
        membership.client.save()
    elif change == "email":
        customer.email = (
            "unmatched@example.test"  # Keep database recipient different from the explicit delivery address.
        )
    elif change == "no_membership":
        membership.delete()
    with pytest.raises(ValidationError):
        issue_customer_email_access(
            actor=manager, recipient_user_id=customer.pk, recipient_email=customer.email, work_date=DAY
        )
    assert CustomerEmailAccessGrant.objects.count() == 0


def test_only_manager_can_issue_or_revoke(access_actors):
    _, customer, other, *_ = access_actors
    with pytest.raises(PermissionDenied):
        issue_customer_email_access(
            actor=other, recipient_user_id=customer.pk, recipient_email=customer.email, work_date=DAY
        )
    with pytest.raises(PermissionDenied):
        revoke_customer_email_access(actor=other, recipient_user_id=customer.pk)


def test_session_marker_cannot_select_another_recipient(access_actors):
    issued = issue(access_actors)
    browser = HttpClient()
    browser.force_login(access_actors[2])
    session = browser.session
    session[EMAIL_ACCESS_SESSION_KEY] = issued.grant_id
    session.save()
    assert browser.get(reverse("customer_portal:home")).status_code == 410
    assert SESSION_KEY not in browser.session


def test_invalid_confirmation_does_not_replace_an_administrator(access_actors):
    issued = issue(access_actors)
    browser = HttpClient()
    browser.force_login(access_actors[0])
    path, data = link_data(issued.works_url)
    data["target"] = "https://evil.example/"
    assert browser.post(path, data).status_code == 410
    assert browser.session[SESSION_KEY] == str(access_actors[0].pk)
