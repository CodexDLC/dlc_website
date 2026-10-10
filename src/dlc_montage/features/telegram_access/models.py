"""Подтверждённые Telegram-идентичности и одноразовые ссылки привязки."""

from typing import ClassVar

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TelegramIdentity(models.Model):
    """Подтверждённый Telegram-аккаунт одного сотрудника."""

    employee = models.OneToOneField(
        "staff.Employee",
        on_delete=models.CASCADE,
        related_name="telegram_identity",
    )
    telegram_user_id = models.BigIntegerField(unique=True, validators=[MinValueValidator(1)])
    private_chat_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["employee__last_name", "employee__first_name"]
        permissions: ClassVar[list[tuple[str, str]]] = [
            ("manage_telegram_access", "Can manage employee Telegram access"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} · {self.telegram_user_id}"


class TelegramLinkToken(models.Model):
    """Хеш одноразового токена, выданного для привязки сотрудника."""

    employee = models.ForeignKey(
        "staff.Employee",
        on_delete=models.CASCADE,
        related_name="telegram_link_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    used_by_telegram_user_id = models.BigIntegerField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_telegram_link_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at", "-pk"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["employee", "expires_at"], name="tg_link_employee_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} · {self.created_at:%Y-%m-%d %H:%M}"
