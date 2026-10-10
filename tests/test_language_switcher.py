"""Language selection preserves the current cabinet page and its filters."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils.translation import override


@pytest.mark.django_db
def test_cabinet_has_visible_language_choices(client):
    user = get_user_model().objects.create_superuser("language-admin", password=None)
    client.force_login(user)
    response = client.get("/ru/cabinet/?q=Berlin&page=2")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'class="crm-language-switcher"' in html
    assert 'value="ru"' in html
    assert 'value="de"' in html
    assert '/ru/cabinet/?q=Berlin&amp;page=2' in html
    assert "DLC Montage</title>" in html


@pytest.mark.parametrize("source,target", [("ru", "de"), ("de", "ru")])
def test_language_post_preserves_page_and_query(client, source, target):
    response = client.post(
        reverse("set_language"),
        {"language": target, "next": f"/{source}/cabinet/customer/objects/?q=Berlin&page=2"},
    )
    assert response.status_code == 302
    assert response.url == f"/{target}/cabinet/customer/objects/?q=Berlin&page=2"
    assert response.cookies["django_language"].value == target


def test_language_change_requires_csrf():
    response = Client(enforce_csrf_checks=True).post(reverse("set_language"), {"language": "de"})
    assert response.status_code == 403


def test_language_change_rejects_external_redirect(client):
    response = client.post(reverse("set_language"), {"language": "de", "next": "https://external.test/"})
    assert response.status_code == 302
    assert not response.url.startswith("https://external.test")


def test_language_change_handles_malformed_redirect(client):
    response = client.post(reverse("set_language"), {"language": "de", "next": "http://["})
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["ru", "de"])
def test_login_has_language_choices(client, language):
    with override(language):
        response = client.get(reverse("cabinet:account_login"))
    assert response.status_code == 200
    assert 'class="crm-language-switcher"' in response.content.decode()
