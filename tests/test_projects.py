"""Контракт общих проектов и AC-объектов."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from features.projects.models import AcObject, Client, ProjectGroup
from features.projects.services import save_group, save_object

pytestmark = pytest.mark.django_db


def test_minimal_group_and_object_access():
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    ordinary = get_user_model().objects.create_user(username="ordinary")
    group = save_group(actor=admin, data={"name": "Berlin"})
    site = save_object(actor=admin, group=group, data={"name": "Haus 42", "address": "Berlin 42"})
    assert site.project_number == ""
    assert site.group == group
    with pytest.raises(PermissionDenied):
        save_object(actor=ordinary, group=group, data={"name": "Haus 40"})
    with pytest.raises(ValidationError):
        save_group(actor=admin, group_id=group.pk, data={"capacity_kw": -1})


def test_group_soft_delete():
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    group = save_group(actor=admin, data={"name": "Berlin"})
    save_group(actor=admin, group_id=group.pk, data={"status": "deleted"})
    assert ProjectGroup.objects.get(pk=group.pk).status == "deleted"
    with pytest.raises(ValidationError):
        group.delete()


def test_group_ac_progress_is_recalculated_from_active_sites():
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    group = save_group(actor=admin, data={"name": "Berlin"})
    first = save_object(actor=admin, group=group, data={"name": "Haus 40"})
    second = save_object(actor=admin, group=group, data={"name": "Haus 42"})

    save_object(actor=admin, group=group, object_id=first.pk, data={"status": "completed"})
    group.refresh_from_db()
    assert group.ac_status == "started"

    save_object(actor=admin, group=group, object_id=second.pk, data={"status": "completed"})
    group.refresh_from_db()
    assert group.ac_status == "completed"


def test_project_choice_searches_name_address_and_client(client):
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    mbg = Client.objects.create(name="MBG Solid Solution")
    ProjectGroup.objects.create(name="Huttwiler Weg", address="Berlin", client=mbg)
    ProjectGroup.objects.create(name="Leipzig Anlage", address="Sachsen")
    client.force_login(admin)

    by_name = client.get(reverse("projects:group_choices"), {"q": "Hutt"}).json()
    by_address = client.get(reverse("projects:group_choices"), {"q": "Berlin"}).json()
    by_client = client.get(reverse("projects:group_choices"), {"q": "MBG"}).json()

    assert [row["label"] for row in by_name["results"]] == ["Huttwiler Weg"]
    assert [row["label"] for row in by_address["results"]] == ["Huttwiler Weg"]
    assert [row["label"] for row in by_client["results"]] == ["Huttwiler Weg"]


def test_site_choice_is_scoped_to_selected_anlage(client):
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    berlin = ProjectGroup.objects.create(name="Berlin")
    leipzig = ProjectGroup.objects.create(name="Leipzig")
    visible = AcObject.objects.create(group=berlin, name="Ragazer Straße 42", project_number="2026-1516")
    AcObject.objects.create(group=leipzig, name="Ragazer Straße 44", project_number="OTHER")
    client.force_login(admin)

    response = client.get(
        reverse("projects:site_choices"),
        {"group": berlin.pk, "q": "1516"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"value": str(visible.pk), "label": "Ragazer Straße 42 · P/Nr 2026-1516", "meta": ""}
    ]
