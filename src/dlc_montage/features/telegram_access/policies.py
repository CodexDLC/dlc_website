"""Права управления Telegram-привязками не зависят от Telegram ID."""


def can_manage_telegram_access(user: object) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (
            getattr(user, "is_superuser", False)
            or user.has_perm("telegram_access.manage_telegram_access")
        )
    )
