"""Own-account access and password change contracts."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from features.customer_portal.models import ClientMembership
from features.projects.models import Client

pytestmark = pytest.mark.django_db
OLD = "StartSecret!7392"
NEW = "ChangedSecret!8463"


@pytest.fixture
def account_user():
    users = get_user_model()
    manager = users.objects.create_superuser(username="account-manager", password=OLD)
    user = users.objects.create_user(
        username="account-owner", password=OLD, first_name="Anna", email="anna@example.test"
    )
    customer = Client.objects.create(name="Account client")
    ClientMembership.objects.create(user=user, client=customer, granted_by=manager)
    return user


@pytest.mark.parametrize("locale", ["ru", "de"])
def test_account_renders_own_details_and_password_fields(client, account_user, locale):
    client.force_login(account_user)
    response = client.get(f"/{locale}/cabinet/customer/account/")
    assert response.status_code == 200
    assert response.context["account_user"] == account_user
    assert b"anna@example.test" in response.content
    assert b'name="old_password"' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content


def test_account_denies_anonymous_and_unassigned_users(client):
    assert client.get("/de/cabinet/customer/account/").status_code == 302
    user = get_user_model().objects.create_user(username="unassigned")
    client.force_login(user)
    assert client.get("/de/cabinet/customer/account/").status_code == 403


@pytest.mark.parametrize(
    "old,new,repeat,field",
    [
        ("wrong", NEW, NEW, "old_password"),
        (OLD, NEW, "different", "new_password2"),
        (OLD, "123", "123", "new_password2"),
    ],
)
def test_account_rejects_invalid_password(client, account_user, old, new, repeat, field):
    client.force_login(account_user)
    response = client.post(
        "/de/cabinet/customer/account/", {"old_password": old, "new_password1": new, "new_password2": repeat}
    )
    assert response.status_code == 200
    assert field in response.context["form"].errors
    account_user.refresh_from_db()
    assert account_user.check_password(OLD)


def test_inactive_membership_denies_account(client, account_user):
    membership = account_user.client_membership
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    client.force_login(account_user)
    assert client.get("/de/cabinet/customer/account/").status_code == 403
    assert (
        client.post(
            "/de/cabinet/customer/account/", {"old_password": OLD, "new_password1": NEW, "new_password2": NEW}
        ).status_code
        == 403
    )
    account_user.refresh_from_db()
    assert account_user.check_password(OLD)


def test_password_change_preserves_session_and_cannot_edit_profile_or_membership(client, account_user):
    other = get_user_model().objects.create_user(username="other-account", password=OLD)
    client.force_login(account_user)
    membership = account_user.client_membership
    response = client.post(
        "/de/cabinet/customer/account/",
        {
            "old_password": OLD,
            "new_password1": NEW,
            "new_password2": NEW,
            "user_id": other.pk,
            "first_name": "Injected",
            "is_superuser": "1",
            "client": "999",
            "can_manage_projects": "1",
        },
    )
    assert response.status_code == 302
    account_user.refresh_from_db()
    other.refresh_from_db()
    membership.refresh_from_db()
    assert account_user.check_password(NEW)
    assert other.check_password(OLD)
    assert account_user.first_name == "Anna" and not account_user.is_superuser
    assert not membership.can_manage_projects
    assert str(client.session["_auth_user_id"]) == str(account_user.pk)
    assert client.get("/de/cabinet/customer/account/").status_code == 200


def test_account_get_cannot_mutate_password_and_post_requires_csrf(account_user):
    client = HttpClient(enforce_csrf_checks=True)
    client.force_login(account_user)
    response = client.get(
        "/de/cabinet/customer/account/", {"old_password": OLD, "new_password1": NEW, "new_password2": NEW}
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/de/cabinet/customer/account/", {"old_password": OLD, "new_password1": NEW, "new_password2": NEW}
        ).status_code
        == 403
    )
    account_user.refresh_from_db()
    assert account_user.check_password(OLD)
