"""Списки доступных проектов и вложений."""

from django.db.models import Q

from features.internal_time.policies import is_manager
from features.projects.selectors import visible_groups

from .models import ProjectFile


def file_groups(user, direction):
    groups = visible_groups(user, direction)
    if not is_manager(user):
        groups = groups.filter(Q(responsible=user) | Q(deputy=user) | Q(ac_responsible=user) | Q(dc_responsible=user))
    return groups


def files_for_group(group, *, kind="", site=""):
    """Вернуть файлы проекта с безопасными фильтрами вида и Standort."""
    files = group.files.select_related("site", "uploaded_by")
    if kind in dict(ProjectFile._meta.get_field("kind").choices):
        files = files.filter(kind=kind)
    if site == "general":
        files = files.filter(site__isnull=True)
    elif str(site).isdigit():
        files = files.filter(site_id=site)
    return files
