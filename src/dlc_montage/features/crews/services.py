"""Запись сохранённых команд; состав отчётов при этом не изменяется."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from features.internal_time.policies import can_report, employee_for, is_manager

from .models import Crew, CrewMember


@transaction.atomic
def save_team(*, actor, name, owner, members, team_id=None):
    """Создать или изменить доступную автору команду."""
    if not can_report(actor):
        raise PermissionDenied
    if not is_manager(actor) and employee_for(actor) != owner:
        raise PermissionDenied
    team = Crew.objects.select_for_update().get(pk=team_id) if team_id else Crew(owner=owner)
    if team_id and not is_manager(actor) and team.owner_id != getattr(employee_for(actor), "pk", None):
        raise PermissionDenied
    members = list(members)
    if not members or any(member.employment_status != "active" for member in members):
        raise ValidationError(_("Выберите действующих сотрудников."))
    if not name.strip():
        raise ValidationError(_("Укажите название команды."))
    if Crew.objects.filter(owner=owner, name=name.strip()).exclude(pk=team_id).exists():
        raise ValidationError(_("У бригадира уже есть команда с таким названием."))
    team.name = name.strip()
    team.owner = owner
    team.full_clean()
    team.save()
    team.memberships.all().delete()
    CrewMember.objects.bulk_create(
        [CrewMember(crew=team, employee=member, position=i) for i, member in enumerate(members)]
    )
    return team
