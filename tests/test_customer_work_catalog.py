from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from features.work_catalog.customer_selectors import customer_positions
from features.work_catalog.customer_services import save_customer_position

pytestmark = pytest.mark.django_db


def test_seed_and_active_order():
    positions = customer_positions()
    assert positions.count() == 21
    assert positions.get(code="01.0200").unit == "unconfirmed"
    assert positions.get(code="01.0200").manual_only
    assert positions.get(code="10.010").unit_price == Decimal("60.00")
    assert positions.get(code="01.0190").manual_only
    positions.get(code="10.010").__class__.objects.filter(code="10.010").update(is_active=False)
    assert customer_positions().count() == 20


def test_service_permissions_validation_and_immutable_code():
    User = get_user_model()
    admin = User.objects.create_user(username="customer-admin", is_superuser=True)
    user = User.objects.create_user(username="customer-user")
    data = dict(
        code="X.1",
        name_de="Test",
        name_ru="Тест",
        unit="piece",
        unit_price=Decimal("1"),
        sort_order=1,
        is_active=True,
        manual_only=False,
        note="",
    )
    with pytest.raises(PermissionDenied):
        save_customer_position(actor=user, data=data)
    item = save_customer_position(actor=admin, data=data)
    with pytest.raises(ValidationError):
        save_customer_position(actor=admin, data={**data, "code": "X.2"}, pk=item.pk)
    with pytest.raises(ValidationError):
        save_customer_position(actor=admin, data={**data, "unit_price": Decimal("-1")}, pk=item.pk)
    item.refresh_from_db()
    assert item.code == "X.1" and item.unit_price == Decimal("1")


def test_catalog_requires_financial_access(client):
    user = get_user_model().objects.create_user(username="ordinary", password="pass")
    client.force_login(user)
    assert client.get(reverse("work_catalog:customer_list")).status_code == 403
    user.is_superuser = True
    user.save()
    assert client.get(reverse("work_catalog:customer_list")).status_code == 200
