"""Права на чувствительные операции с отчётами MBG."""


def can_export_reports(user):
    """Экспорт и сводные данные доступны только администраторам."""
    return bool(user.is_authenticated and user.is_active and user.is_superuser)
