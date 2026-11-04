import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from features.mbg_reports.models import CustomerWorkPackage
from features.projects.models import AcObject, ProjectGroup
from features.projects.services import save_site_work_item
from features.work_catalog.models import CustomerWorkPosition, WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    user = get_user_model().objects.create_user(username="billing-owner", is_superuser=True)
    group = ProjectGroup.objects.create(name="Billing")
    site = AcObject.objects.create(group=group, name="Haus", address="Straße 1", project_number="P-1", status="started")
    other = AcObject.objects.create(
        group=group, name="Other", address="Straße 2", project_number="P-2", status="started"
    )
    item = save_site_work_item(
        actor=user, site=site, work_type=WorkType.objects.get(code="uv-montage"), label="UV", planned_quantity=1
    )
    foreign = save_site_work_item(
        actor=user, site=other, work_type=WorkType.objects.get(code="uv-montage"), label="Other UV", planned_quantity=1
    )
    return user, site, item, foreign


def test_access_and_read_only_get(client, setup_data):
    user, site, _item, _foreign = setup_data
    url = reverse("mbg_reports:customer_billing", args=[site.pk])
    ordinary = get_user_model().objects.create_user(username="ordinary")
    client.force_login(ordinary)
    assert client.get(url).status_code == 403
    assert client.post(url, {"action": "prepare"}).status_code == 403
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    assert "10.010" in response.content.decode()
    assert not CustomerWorkPackage.objects.exists()
    assert client.post(url, {"action": "prepare"}).status_code == 302


def test_package_form_limits_site_and_uses_service(client, setup_data):
    user, site, item, foreign = setup_data
    client.force_login(user)
    url = reverse("mbg_reports:customer_package_new", args=[site.pk])
    position = CustomerWorkPosition.objects.get(code="10.010")
    data = {"position": position.pk, "label": "UV", "quantity": "1", "items": [foreign.pk], "is_active": "on"}
    response = client.post(url, data)
    assert response.status_code == 200
    assert not CustomerWorkPackage.objects.exists()
    data["items"] = [item.pk]
    response = client.post(url, data)
    assert response.status_code == 200 and not CustomerWorkPackage.objects.exists()
    connect = save_site_work_item(
        actor=user,
        site=site,
        work_type=WorkType.objects.get(code="uv-anschluss"),
        label="UV Anschluss",
        planned_quantity=1,
    )
    data["items"] = [item.pk, connect.pk]
    assert client.post(url, data).status_code == 302
    package = CustomerWorkPackage.objects.get()
    edit = reverse("mbg_reports:customer_package_edit", args=[site.pk, package.pk])
    response = client.get(edit)
    assert response.status_code == 200 and set(response.context["form"].initial["items"]) == {item.pk, connect.pk}


def test_manual_position_and_csrf(setup_data):
    user, site, _item, _foreign = setup_data
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("mbg_reports:customer_package_new", args=[site.pk])
    data = {
        "position": CustomerWorkPosition.objects.get(code="01.0200").pk,
        "label": "Com.Box",
        "quantity": "2",
        "is_active": "on",
    }
    assert client.post(url, data).status_code == 403
    client.get(url)
    data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
    response = client.post(url, data)
    assert response.status_code == 200 and not CustomerWorkPackage.objects.exists()
    data.update(manual_confirmed="on", note="Aufmaß bestätigt")
    assert client.post(url, data).status_code == 302


def test_retire_package_with_inactive_position_and_old_components(client, setup_data):
    from features.mbg_reports.customer_billing_services import save_customer_package

    user, site, work, _foreign = setup_data
    client.force_login(user)
    position = CustomerWorkPosition.objects.get(code="01.0020")
    package = save_customer_package(
        actor=user, site=site, position=position, label="Old package", quantity=1, items=[work], note="Explicit mapping"
    )
    position.is_active = False
    position.save(update_fields=["is_active"])
    work.is_required = False
    work.save(update_fields=["is_required"])
    url = reverse("mbg_reports:customer_package_edit", args=[site.pk, package.pk])
    response = client.post(
        url,
        {
            "position": position.pk,
            "label": package.label,
            "quantity": "1",
            "items": [work.pk],
            "note": "Replaced mapping",
        },
    )
    assert response.status_code == 302
    package.refresh_from_db()
    assert not package.is_active
