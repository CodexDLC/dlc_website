"""Привязка Telegram не заменяет права сотрудника и не хранит открытые токены."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from features.staff.models import Employee
from features.telegram_access.models import TelegramIdentity, TelegramLinkToken
from features.telegram_access.services import (
    consume_link_token,
    deactivate_identity,
    issue_link_token,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def people():
    User = get_user_model()
    admin = User.objects.create_user(username="admin", is_superuser=True)
    regular = User.objects.create_user(username="regular")
    first = Employee.objects.create(first_name="Dmytro", last_name="Sukhovyi", is_foreman=True)
    second = Employee.objects.create(first_name="Mykhailo", last_name="Abasov", is_foreman=True)
    return admin, regular, first, second


def test_issue_and_consume_large_telegram_id(people):
    admin, _, employee, _ = people
    issued = issue_link_token(actor=admin, employee_id=employee.pk)

    assert issued.token not in issued.record.token_hash
    assert len(issued.record.token_hash) == 64

    telegram_user_id = 2**40 + 123
    identity = consume_link_token(
        token=issued.token,
        telegram_user_id=telegram_user_id,
        username="@dmytro",
        private_chat_id=telegram_user_id,
    )

    assert identity.employee == employee
    assert identity.telegram_user_id == telegram_user_id
    assert identity.username == "dmytro"
    issued.record.refresh_from_db()
    assert issued.record.used_at is not None
    assert issued.record.used_by_telegram_user_id == telegram_user_id
    with pytest.raises(ValidationError):
        consume_link_token(token=issued.token, telegram_user_id=telegram_user_id)


def test_only_manager_can_issue_or_disable_access(people):
    admin, regular, employee, _ = people
    with pytest.raises(PermissionDenied):
        issue_link_token(actor=regular, employee_id=employee.pk)

    issued = issue_link_token(actor=admin, employee_id=employee.pk)
    identity = consume_link_token(token=issued.token, telegram_user_id=123456789)
    with pytest.raises(PermissionDenied):
        deactivate_identity(actor=regular, employee_id=employee.pk)

    deactivate_identity(actor=admin, employee_id=employee.pk)
    identity.refresh_from_db()
    assert not identity.is_active


def test_new_link_revokes_previous_and_expired_link_is_rejected(people):
    admin, _, employee, _ = people
    first = issue_link_token(actor=admin, employee_id=employee.pk)
    second = issue_link_token(actor=admin, employee_id=employee.pk)
    first.record.refresh_from_db()
    assert first.record.revoked_at is not None

    with pytest.raises(ValidationError):
        consume_link_token(token=first.token, telegram_user_id=111)

    second.record.expires_at = timezone.now() - timedelta(seconds=1)
    second.record.save(update_fields=["expires_at"])
    with pytest.raises(ValidationError):
        consume_link_token(token=second.token, telegram_user_id=111)


def test_identity_cannot_be_shared_or_silently_relinked(people):
    admin, _, first_employee, second_employee = people
    first_link = issue_link_token(actor=admin, employee_id=first_employee.pk)
    consume_link_token(token=first_link.token, telegram_user_id=777)

    second_link = issue_link_token(actor=admin, employee_id=second_employee.pk)
    with pytest.raises(ValidationError):
        consume_link_token(token=second_link.token, telegram_user_id=777)

    replacement = issue_link_token(actor=admin, employee_id=first_employee.pk)
    with pytest.raises(ValidationError):
        consume_link_token(token=replacement.token, telegram_user_id=888)

    assert TelegramIdentity.objects.count() == 1
    assert TelegramLinkToken.objects.filter(used_at__isnull=False).count() == 1
