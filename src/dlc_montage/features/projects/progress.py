"""Materialized progress for Anlagen and their AC Standorte."""

from django.db import transaction

from .models import AcObject, ProjectGroup


@transaction.atomic
def mark_site_started(*, site_id):
    """Record the first operational fact for a Standort and its AC direction."""
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site_id)
    if site.status == "not_started":
        site.status = "started"
        site.save(update_fields=["status"])
    mark_group_direction_started(group_id=site.group_id, direction="ac")
    return site


@transaction.atomic
def mark_group_direction_started(*, group_id, direction):
    """Start one direction without changing the administrative project lifecycle."""
    if direction not in {"ac", "dc"}:
        raise ValueError("Unknown project direction.")
    group = ProjectGroup.objects.select_for_update().get(pk=group_id)
    field = f"{direction}_status"
    if getattr(group, field) == "not_started":
        setattr(group, field, "started")
        group.save(update_fields=[field])
    return group


@transaction.atomic
def synchronize_ac_progress(*, group_id):
    """Recalculate AC progress after an administrator changes a Standort."""
    group = ProjectGroup.objects.select_for_update().get(pk=group_id)
    statuses = list(
        AcObject.objects.filter(group=group, is_active=True).values_list("status", flat=True)
    )
    if statuses and all(status == "completed" for status in statuses):
        target = "completed"
    elif any(status in {"started", "completed"} for status in statuses):
        target = "started"
    elif group.team_reports.filter(direction="ac").exists():
        target = "started"
    else:
        target = "not_started"
    if group.ac_status != target:
        group.ac_status = target
        group.save(update_fields=["ac_status"])
    return group
