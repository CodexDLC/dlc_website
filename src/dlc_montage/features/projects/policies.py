"""Доступ к общим проектам и техническим материалам."""

from features.internal_time.policies import can_report, directions_for, is_manager


def can_view_group(user, group):
    return is_manager(user) or (
        can_report(user)
        and group.status != "deleted"
        and any(getattr(group, f"has_{key}") for key in dict(directions_for(user)))
    )


def is_assigned(user, group):
    return user.is_authenticated and user.pk in (
        group.responsible_id,
        group.deputy_id,
        group.ac_responsible_id,
        group.dc_responsible_id,
    )


def can_edit_group(user, group):
    return is_manager(user) or (
        can_view_group(user, group) and group.edit_level == "foreman" and is_assigned(user, group)
    )


def can_use_files(user, group):
    return is_manager(user) or (can_view_group(user, group) and is_assigned(user, group))
