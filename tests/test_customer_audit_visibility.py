"""История решений заказчика отделена от внутренней подготовки данных."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from features.customer_portal.models import ClientMembership, CustomerAuditEvent
from features.customer_portal.selectors import audit_events_for_actor
from features.projects.models import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def audit_setup():
    users = get_user_model()
    manager = users.objects.create_superuser("audit-manager", "manager@example.test", None)
    customer = users.objects.create_user("audit-customer")
    company = Client.objects.create(name="Audit company")
    other_company = Client.objects.create(name="Other audit company")
    ClientMembership.objects.create(user=customer, client=company, granted_by=manager)
    return manager, customer, company, other_company


def event(actor, company, action):
    return CustomerAuditEvent.objects.create(
        actor=actor, client=company, action=action, target_type="SiteReview", target_id=1
    )


def test_customer_audit_hides_preparation_but_keeps_real_decisions(audit_setup, client):
    manager, customer, company, other_company = audit_setup
    hidden = [
        event(manager, company, action)
        for action in ("review_snapshot_prepared", "review_submitted", "site_updated", "membership_saved")
    ]
    visible = [event(customer, company, action) for action in ("plan_proposed", "plan_reviewed", "review_decided")]
    foreign = event(manager, other_company, "review_decided")
    client.force_login(customer)
    response = client.get(reverse("customer_portal:audit"))
    assert response.status_code == 200
    assert {row.pk for row in response.context["events"]} == {row.pk for row in visible}
    assert foreign.pk not in {row.pk for row in response.context["events"]}
    assert CustomerAuditEvent.objects.filter(pk__in=[row.pk for row in hidden]).count() == len(hidden)


def test_customer_audit_is_empty_after_only_internal_preparation(audit_setup, client):
    manager, customer, company, _ = audit_setup
    event(manager, company, "review_submitted")
    event(manager, company, "review_snapshot_prepared")
    client.force_login(customer)
    response = client.get(reverse("customer_portal:audit"))
    assert response.status_code == 200
    assert response.context["events"].paginator.count == 0


def test_manager_retains_full_audit_and_unassigned_user_sees_nothing(audit_setup):
    manager, _customer, company, other_company = audit_setup
    own = event(manager, company, "review_snapshot_prepared")
    other = event(manager, other_company, "review_submitted")
    assert set(audit_events_for_actor(manager).values_list("pk", flat=True)) == {own.pk, other.pk}
    outsider = get_user_model().objects.create_user("audit-outsider")
    assert not audit_events_for_actor(outsider).exists()
