"""Доступ к отчётам проверяется одинаково из любого интерфейса."""

from datetime import timedelta

from django.utils import timezone


def is_manager(user):
    return (
        user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.has_perm("internal_time.manage_reports"))
    )


def employee_for(user):
    return getattr(user, "employee", None)


def can_report(user):
    employee = employee_for(user)
    return bool(
        user.is_authenticated
        and user.is_active
        and (is_manager(user) or user.has_perm("internal_time.submit_reports") or (employee and employee.is_foreman))
    )


def directions_for(user):
    if is_manager(user):
        return [("ac", "AC"), ("dc", "DC")]
    employee = employee_for(user)
    return [
        (key, key.upper())
        for key in ("ac", "dc")
        if user.has_perm(f"internal_time.access_{key}") or (employee and getattr(employee, f"has_{key}_access"))
    ]


def can_edit(user, report):
    if is_manager(user):
        return True
    return bool(
        can_report(user)
        and report.author_id == user.pk
        and report.direction in dict(directions_for(user))
        and report.status != report.Status.ACCEPTED
        and (report.submitted_at is None or timezone.now() <= report.submitted_at + timedelta(days=7))
    )


def can_create_group(user):
    return is_manager(user) or (can_report(user) and user.has_perm("projects.quick_create_projectgroup"))
