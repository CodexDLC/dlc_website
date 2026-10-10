"""Use cases безопасной выдачи и применения Telegram-ссылок."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.staff.models import Employee

from .models import TelegramIdentity, TelegramLinkToken
from .policies import can_manage_telegram_access

MAX_LINK_LIFETIME = timedelta(days=7)
DEFAULT_LINK_LIFETIME = timedelta(hours=24)
INVALID_LINK_MESSAGE = _("Ссылка Telegram недействительна или истекла.")


@dataclass(frozen=True, slots=True)
class IssuedTelegramLink:
    """Одноразовый открытый токен и его сохранённая запись."""

    token: str
    record: TelegramLinkToken


def token_digest(token: str) -> str:
    """Получить сохраняемый SHA-256 digest открытого токена."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@transaction.atomic
def issue_link_token(
    *,
    actor: object,
    employee_id: int,
    lifetime: timedelta = DEFAULT_LINK_LIFETIME,
) -> IssuedTelegramLink:
    """Выдать сотруднику новую ссылку и отозвать прошлые неиспользованные ссылки."""
    if not can_manage_telegram_access(actor):
        raise PermissionDenied
    if lifetime <= timedelta(0) or lifetime > MAX_LINK_LIFETIME:
        raise ValidationError(_("Ссылка должна действовать от одной секунды до семи суток."))

    employee = Employee.objects.select_for_update().get(pk=employee_id)
    if employee.employment_status != Employee.EmploymentStatus.ACTIVE:
        raise ValidationError(_("Telegram можно привязать только действующему сотруднику."))

    now = timezone.now()
    TelegramLinkToken.objects.filter(
        employee=employee,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now)

    raw_token = secrets.token_urlsafe(32)
    record = TelegramLinkToken.objects.create(
        employee=employee,
        token_hash=token_digest(raw_token),
        expires_at=now + lifetime,
        created_by=actor,
    )
    return IssuedTelegramLink(token=raw_token, record=record)


def _valid_telegram_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


@transaction.atomic
def consume_link_token(
    *,
    token: str,
    telegram_user_id: int,
    username: str = "",
    private_chat_id: int | None = None,
) -> TelegramIdentity:
    """Однократно связать подтверждённого Telegram-пользователя с сотрудником."""
    if not token or not _valid_telegram_id(telegram_user_id):
        raise ValidationError(INVALID_LINK_MESSAGE)
    if private_chat_id is not None and not isinstance(private_chat_id, int):
        raise ValidationError(_("Некорректный идентификатор Telegram-чата."))

    try:
        link = (
            TelegramLinkToken.objects.select_for_update().select_related("employee").get(token_hash=token_digest(token))
        )
    except TelegramLinkToken.DoesNotExist as exc:
        raise ValidationError(INVALID_LINK_MESSAGE) from exc

    now = timezone.now()
    if link.used_at or link.revoked_at or link.expires_at <= now:
        raise ValidationError(INVALID_LINK_MESSAGE)
    if link.employee.employment_status != Employee.EmploymentStatus.ACTIVE:
        raise ValidationError(_("Доступ сотрудника отключён."))

    occupied = TelegramIdentity.objects.select_for_update().filter(telegram_user_id=telegram_user_id).first()
    if occupied and occupied.employee_id != link.employee_id:
        raise ValidationError(_("Этот Telegram-аккаунт уже связан с другим сотрудником."))

    identity = TelegramIdentity.objects.select_for_update().filter(employee=link.employee).first()
    if identity and identity.telegram_user_id != telegram_user_id:
        raise ValidationError(_("У сотрудника уже есть другая Telegram-привязка."))

    if identity is None:
        identity = TelegramIdentity(employee=link.employee, telegram_user_id=telegram_user_id)
    identity.username = username.lstrip("@")[:64]
    identity.private_chat_id = private_chat_id
    identity.is_active = True
    identity.verified_at = now
    identity.full_clean()
    identity.save()

    link.used_at = now
    link.used_by_telegram_user_id = telegram_user_id
    link.save(update_fields=["used_at", "used_by_telegram_user_id"])
    return identity


@transaction.atomic
def deactivate_identity(*, actor: object, employee_id: int) -> TelegramIdentity:
    """Отключить Telegram-доступ без удаления аудируемой привязки."""
    if not can_manage_telegram_access(actor):
        raise PermissionDenied
    identity = TelegramIdentity.objects.select_for_update().get(employee_id=employee_id)
    identity.is_active = False
    identity.save(update_fields=["is_active", "updated_at"])
    TelegramLinkToken.objects.filter(
        employee_id=employee_id,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
    return identity
