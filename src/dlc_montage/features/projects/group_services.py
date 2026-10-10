"""Минимальное создание общего проекта."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from features.integrations.nextcloud import ensure_group_folders

from .models import ProjectGroup


@transaction.atomic
def create_project_group(*, actor, name):
    """Создать первичную запись; автор становится ответственным."""
    from features.internal_time.policies import can_create_group

    if not can_create_group(actor):
        raise PermissionDenied
    name = name.strip()
    if not name or len(name) > 255:
        raise ValidationError(_("Укажите название проекта длиной до 255 символов."))
    if ProjectGroup.objects.filter(name__iexact=name).exists():
        raise ValidationError(_("Такой проект уже есть. Выберите его в списке."))
    group = ProjectGroup.objects.create(name=name, responsible=actor)
    transaction.on_commit(lambda: ensure_group_folders(group))
    return group
