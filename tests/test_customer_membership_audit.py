"""Тесты аудита назначения доступа заказчика (grant_membership)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from features.customer_portal.models import CustomerAuditEvent
from features.customer_portal.services import grant_membership
from features.projects.models import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    users = get_user_model()
    manager_1 = users.objects.create_superuser(
        username="manager-1", email="manager1@example.test", password=None
    )
    manager_2 = users.objects.create_superuser(
        username="manager-2", email="manager2@example.test", password=None
    )
    user = users.objects.create_user(username="customer-user")
    client_a = Client.objects.create(name="Auftraggeber Alpha", is_active=True)
    client_b = Client.objects.create(name="Auftraggeber Beta", is_active=True)
    return manager_1, manager_2, user, client_a, client_b


def test_membership_creation_audited(actors):
    manager_1, _manager_2, user, client_a, _client_b = actors
    membership = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=False,
        is_active=True,
    )
    assert membership.client == client_a
    assert membership.granted_by == manager_1

    events = CustomerAuditEvent.objects.filter(target_id=membership.pk, action="membership_saved")
    assert events.count() == 1
    event = events.first()
    assert event.client == client_a
    assert event.actor == manager_1
    assert event.before == {}
    assert event.after == {
        "user_id": user.pk,
        "client_id": client_a.pk,
        "active": True,
        "can_manage_projects": False,
    }


def test_client_change_creates_audit_events_for_new_and_previous_client(actors):
    manager_1, manager_2, user, client_a, client_b = actors
    membership = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=False,
        is_active=True,
    )
    initial_event = CustomerAuditEvent.objects.get(
        target_id=membership.pk, client=client_a, action="membership_saved"
    )

    # Смена заказчика другим менеджером
    updated = grant_membership(
        actor=manager_2,
        user=user,
        client=client_b,
        can_manage_projects=True,
        is_active=True,
    )
    assert updated.client == client_b
    assert updated.granted_by == manager_2

    # Должно появиться 2 новых события: одно для client_b, одно для client_a
    new_event = CustomerAuditEvent.objects.get(
        target_id=membership.pk, client=client_b, action="membership_saved"
    )

    old_event = CustomerAuditEvent.objects.filter(
        target_id=membership.pk, client=client_a, action="membership_saved"
    ).exclude(pk=initial_event.pk).get()

    expected_before = {
        "client_id": client_a.pk,
        "active": True,
        "can_manage_projects": False,
    }
    expected_after = {
        "user_id": user.pk,
        "client_id": client_b.pk,
        "active": True,
        "can_manage_projects": True,
    }

    assert new_event.actor == manager_2
    assert old_event.actor == manager_2
    assert new_event.before == expected_before
    assert old_event.before == expected_before
    assert new_event.after == expected_after
    assert old_event.after == expected_after


def test_unchanged_membership_does_not_create_events_and_does_not_change_granted_by(actors):
    manager_1, manager_2, user, client_a, _client_b = actors
    membership = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=True,
        is_active=True,
    )
    initial_event_count = CustomerAuditEvent.objects.count()
    assert initial_event_count == 1
    assert membership.granted_by == manager_1

    # Повторный вызов с теми же параметрами другим менеджером
    res = grant_membership(
        actor=manager_2,
        user=user,
        client=client_a,
        can_manage_projects=True,
        is_active=True,
    )

    # Событий добавиться не должно
    assert CustomerAuditEvent.objects.count() == initial_event_count
    # granted_by не должен измениться
    membership.refresh_from_db()
    assert membership.granted_by == manager_1
    assert res.granted_by == manager_1


def test_access_revocation_audited_as_single_event(actors):
    manager_1, _manager_2, user, client_a, _client_b = actors
    membership = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=True,
        is_active=True,
    )
    assert CustomerAuditEvent.objects.count() == 1

    revoked = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=True,
        is_active=False,
    )
    assert not revoked.is_active

    events = CustomerAuditEvent.objects.filter(
        target_id=membership.pk, client=client_a, action="membership_saved"
    ).order_by("created_at", "pk")
    assert events.count() == 2
    revocation_event = events.last()
    assert revocation_event.actor == manager_1
    assert revocation_event.before == {
        "client_id": client_a.pk,
        "active": True,
        "can_manage_projects": True,
    }
    assert revocation_event.after == {
        "user_id": user.pk,
        "client_id": client_a.pk,
        "active": False,
        "can_manage_projects": True,
    }


def test_capability_change_within_company_creates_single_event(actors):
    manager_1, _manager_2, user, client_a, _client_b = actors
    membership = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=False,
        is_active=True,
    )
    assert CustomerAuditEvent.objects.count() == 1

    changed = grant_membership(
        actor=manager_1,
        user=user,
        client=client_a,
        can_manage_projects=True,
        is_active=True,
    )
    assert changed.can_manage_projects

    events = CustomerAuditEvent.objects.filter(
        target_id=membership.pk, client=client_a, action="membership_saved"
    ).order_by("created_at", "pk")
    assert events.count() == 2
    change_event = events.last()
    assert change_event.actor == manager_1
    assert change_event.before == {
        "client_id": client_a.pk,
        "active": True,
        "can_manage_projects": False,
    }
    assert change_event.after == {
        "user_id": user.pk,
        "client_id": client_a.pk,
        "active": True,
        "can_manage_projects": True,
    }


def test_grant_membership_permissions_and_validations(actors):
    manager_1, _manager_2, user, client_a, _client_b = actors
    users = get_user_model()
    plain_user = users.objects.create_user(username="regular-user")

    with pytest.raises(PermissionDenied):
        grant_membership(actor=plain_user, user=user, client=client_a)

    with pytest.raises(ValidationError):
        grant_membership(actor=manager_1, user=manager_1, client=client_a)

    inactive_client = Client.objects.create(name="Inactive Client", is_active=False)
    with pytest.raises(ValidationError):
        grant_membership(actor=manager_1, user=user, client=inactive_client)

    inactive_user = users.objects.create_user(username="inactive-user", is_active=False)
    with pytest.raises(ValidationError):
        grant_membership(actor=manager_1, user=inactive_user, client=client_a)
