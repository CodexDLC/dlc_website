"""Явная граница доступа к данным одного заказчика."""

from django.core.exceptions import PermissionDenied

from features.internal_time.policies import is_manager

from .models import ClientMembership


def membership_for(user):
    """Вернуть действующее назначение без поиска заказчика по почте."""
    if not user.is_authenticated or not user.is_active:
        return None
    return (
        ClientMembership.objects.select_related("client")
        .filter(user=user, is_active=True, client__is_active=True)
        .first()
    )


def require_customer_group(actor, group, *, manage=False):
    """Разрешить клиентские AC-проекты с проверкой назначения заказчика."""
    if not group.has_ac:
        raise PermissionDenied
    if is_manager(actor):
        return
    membership = membership_for(actor)
    if membership is None or group.client_id != membership.client_id or (manage and not membership.can_manage_projects):
        raise PermissionDenied


def require_customer_site(actor, site, *, manage=False):
    """Проверить принадлежность Standort через родительскую Anlage."""
    require_customer_group(actor, site.group, manage=manage)
