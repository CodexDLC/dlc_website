"""Общая запись клиентского аудита для клиентских и внутренних сервисов."""

from decimal import Decimal

from .models import CustomerAuditEvent

GROUP_AUDIT_FIELDS = (
    "name",
    "address",
    "additional_addresses",
    "capacity_kw",
    "maps_url",
    "starts_on",
    "ends_on",
    "has_ac",
    "has_dc",
)
SITE_AUDIT_FIELDS = ("name", "address", "project_number", "status", "is_active")


def _plain(value):
    """Привести значение поля к JSON-совместимому виду."""
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def group_snapshot(group):
    """Снимок публичных полей Anlage без внутренних назначений."""
    return {key: _plain(value) for key in GROUP_AUDIT_FIELDS if (value := getattr(group, key)) is not None}


def site_snapshot(site):
    """Снимок адресных полей и статуса Standort."""
    return {key: _plain(getattr(site, key)) for key in SITE_AUDIT_FIELDS}


def work_item_snapshot(item):
    """Снимок плановой позиции без цен, ставок и часов."""
    return {
        "site_id": item.site_id,
        "label": item.label,
        "work_type_code": item.work_type.code,
        "route_code": item.route.code if item.route_id else None,
        "cable_type_code": item.cable_type.code if item.cable_type_id else None,
        "planned_quantity": _plain(item.planned_quantity),
        "with_underconstruction": item.with_underconstruction,
        "is_required": item.is_required,
        "not_required_reason": item.not_required_reason,
        "completion_confirmed": item.completion_confirmed_at is not None,
    }


def client_for(target):
    """Определить заказчика объекта аудита; None, если он не назначен."""
    from features.projects.models import AcObject, ProjectGroup

    from .models import ClientMembership

    if isinstance(target, ClientMembership | ProjectGroup):
        return target.client
    if isinstance(target, AcObject):
        return target.group.client
    if hasattr(target, "group"):
        return target.group.client
    return target.site.group.client


def record_event(*, actor, action, target, before=None, after=None, reason="", client=None):
    """Записать неизменяемое событие; без заказчика аудит пропускается."""
    client = client or client_for(target)
    if client is None:
        return None
    return CustomerAuditEvent.objects.create(
        actor=actor,
        client=client,
        action=action,
        target_type=target.__class__.__name__,
        target_id=target.pk,
        before=before or {},
        after=after or {},
        reason=reason,
    )
