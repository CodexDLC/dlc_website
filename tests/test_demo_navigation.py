"""Демо доступно заказчику без расширения доступа к рабочей CRM."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from features.customer_portal.models import ClientMembership
from features.projects.models import Client

pytestmark = pytest.mark.django_db


def test_customer_can_open_demo_but_not_internal_workspace(client):
    actor = get_user_model().objects.create_user(username="demo-customer")
    manager = get_user_model().objects.create_superuser(username="demo-granter", password=None)
    ClientMembership.objects.create(user=actor, client=Client.objects.create(name="Demo customer"), granted_by=manager)
    client.force_login(actor)
    response = client.get(reverse("demo:work_types"))
    assert response.status_code == 200
    assert "Tätigkeiten" in response.content.decode()
    assert "Demo" in response.content.decode()
    response = client.get(reverse("customer_portal:home"))
    assert reverse("demo:work_types") in response.content.decode()
    assert client.get("/ru/cabinet/ac/objects/").status_code == 403
    report_form = client.get(reverse("demo:report_new"))
    assert "Tätigkeit auswählen" in report_form.content.decode()
    assert "Select an option" not in report_form.content.decode()


def test_administrator_sees_demo_in_navigation(client):
    actor = get_user_model().objects.create_superuser(username="demo-admin", password=None)
    client.force_login(actor)
    response = client.get(reverse("customer_portal:home"))
    assert response.status_code == 200
    assert reverse("demo:work_types") in response.content.decode()


def test_demo_requires_login(client):
    response = client.get(reverse("demo:work_types"))
    assert response.status_code == 302
    assert "login" in response.url


def test_demo_reset_requires_csrf_token():
    from django.test import Client as HttpClient
    from features.demo.services import ensure_workspace

    actor = get_user_model().objects.create_user(username="demo-csrf")
    workspace = ensure_workspace(actor)
    report_id = workspace.reports.get().pk
    browser = HttpClient(enforce_csrf_checks=True)
    browser.force_login(actor)
    assert browser.post(reverse("demo:reset")).status_code == 403
    assert workspace.reports.get().pk == report_id
