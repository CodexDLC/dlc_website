"""Транзакции редактирования проектов и объектов."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from features.customer_portal.audit import group_snapshot, record_event, site_snapshot, work_item_snapshot
from features.integrations.nextcloud import ensure_group_folders, ensure_site_folders
from features.internal_time.policies import is_manager
from features.work_catalog.models import CableRoute, CableType, WorkType

from .models import AcObject, Client, ProjectGroup, SiteWorkItem
from .policies import can_edit_group
from .progress import synchronize_ac_progress
from .typical_plan import TypicalPlanConfig, build_typical_plan


@transaction.atomic
def save_group(*, actor, data, group_id=None):
    """Сохранить карточку; назначения и права изменяет администратор."""
    group = ProjectGroup.objects.select_for_update().get(pk=group_id) if group_id else ProjectGroup(responsible=actor)
    if not is_manager(actor) and (not group_id or not can_edit_group(actor, group)):
        raise PermissionDenied
    allowed = {f.name for f in ProjectGroup._meta.fields} - {"id", "created_at"}
    restricted = {
        "responsible",
        "deputy",
        "ac_responsible",
        "dc_responsible",
        "edit_level",
        "status",
        "has_ac",
        "has_dc",
    }
    if not is_manager(actor) and restricted.intersection(data):
        raise PermissionDenied
    before = group_snapshot(group) if group_id else {}
    previous_client = group.client if group_id else None
    for key, value in data.items():
        if key in allowed:
            setattr(group, key, value)
    group.full_clean()
    group.save()
    after = group_snapshot(group)
    if before != after or previous_client != group.client:
        action = "group_updated" if group_id else "group_created"
        record_event(actor=actor, action=action, target=group, before=before, after=after)
        if previous_client is not None and previous_client != group.client:
            record_event(actor=actor, action=action, target=group, before=before, after=after, client=previous_client)
    transaction.on_commit(lambda: ensure_group_folders(group))
    return group


@transaction.atomic
def save_object(*, actor, group, data, object_id=None):
    """AC-объекты пока ведёт только администратор."""
    if not is_manager(actor):
        raise PermissionDenied
    obj = AcObject.objects.select_for_update().get(pk=object_id, group=group) if object_id else AcObject(group=group)
    before = site_snapshot(obj) if object_id else {}
    for key in ("name", "address", "project_number", "status", "is_active"):
        if key in data:
            setattr(obj, key, data[key])
    if object_id and obj.status == "completed":
        previous_status = AcObject.objects.filter(pk=object_id).values_list("status", flat=True).get()
        if previous_status != "completed":
            _validate_site_completion(obj)
    obj.full_clean()
    obj.save()
    after = site_snapshot(obj)
    if before != after:
        record_event(
            actor=actor,
            action="site_updated" if object_id else "site_created",
            target=obj,
            before=before,
            after=after,
        )
    if data.get("status") == "completed":
        _submit_completed_site_for_review(actor=actor, site=obj)
    synchronize_ac_progress(group_id=group.pk)
    transaction.on_commit(lambda: ensure_site_folders(obj))
    return obj


def _submit_completed_site_for_review(*, actor, site):
    """Передать завершённый Standort заказчику, сохранив открытую проверку и приёмку."""
    from features.customer_portal.models import SiteReview
    from features.customer_portal.services import submit_for_review

    if site.group.client_id is None:
        return
    review = SiteReview.objects.select_for_update().filter(site=site).first()
    if review is not None and review.status in {"submitted", "accepted"}:
        return
    submit_for_review(actor=actor, site=site)


def _validate_site_completion(site):
    """Закрывать отслеживаемый Standort только после обязательных позиций."""
    from .read_models import site_work_plan

    plan = site_work_plan(site)
    if plan.is_ready is False:
        raise ValidationError("Pflichtpositionen im Standort-Plan sind noch nicht abgeschlossen.")


@transaction.atomic
def set_site_status(*, actor, site, status):
    """Менять статус Standort с проверкой готовности плана."""
    if not is_manager(actor):
        raise PermissionDenied
    valid = {choice[0] for choice in AcObject._meta.get_field("status").choices}
    if status not in valid:
        raise ValidationError("Ungültiger Standort-Status.")
    site = AcObject.objects.select_for_update().get(pk=site.pk)
    if status == "completed" and site.status != "completed":
        _validate_site_completion(site)
    previous_status = site.status
    site.status = status
    site.save(update_fields=["status"])
    if previous_status != status:
        record_event(
            actor=actor,
            action="site_status_changed",
            target=site,
            before={"status": previous_status},
            after={"status": status},
        )
    if status == "completed":
        _submit_completed_site_for_review(actor=actor, site=site)
    synchronize_ac_progress(group_id=site.group_id)
    return site


@transaction.atomic
def set_work_item_lifecycle(*, actor, item, action, reason=""):
    """Подтвердить, исключить или открыть позицию без изменения MBG."""
    if not is_manager(actor):
        raise PermissionDenied
    item = SiteWorkItem.objects.select_for_update().get(pk=item.pk)
    before = work_item_snapshot(item)
    if action == "confirm":
        from .read_models import site_work_plan

        row = next(row for row in site_work_plan(item.site).rows if row.item.pk == item.pk)
        if row.completed_quantity < item.planned_quantity:
            raise ValidationError("Bestätigter Umfang liegt unter dem Plan. Zuerst Plan oder Bericht korrigieren.")
        item.is_required = True
        item.not_required_reason = ""
        item.not_required_at = None
        item.not_required_by = None
        item.completion_confirmed_at = timezone.now()
        item.completion_confirmed_by = actor
    elif action == "not_required":
        if not reason.strip():
            raise ValidationError("Für 'nicht erforderlich' ist eine Begründung nötig.")
        item.is_required = False
        item.not_required_reason = reason.strip()
        item.not_required_at = timezone.now()
        item.not_required_by = actor
        item.completion_confirmed_at = None
        item.completion_confirmed_by = None
    elif action == "reopen":
        item.is_required = True
        item.not_required_reason = ""
        item.not_required_at = None
        item.not_required_by = None
        item.completion_confirmed_at = None
        item.completion_confirmed_by = None
    else:
        raise ValidationError("Ungültige Aktion für die Planposition.")
    item.save(
        update_fields=[
            "is_required",
            "not_required_reason",
            "not_required_at",
            "not_required_by",
            "completion_confirmed_at",
            "completion_confirmed_by",
        ]
    )
    after = work_item_snapshot(item)
    if before != after:
        record_event(
            actor=actor, action="work_item_lifecycle", target=item, before=before, after=after, reason=reason.strip()
        )
    return item


@transaction.atomic
def save_client(*, actor, data, client_id=None):
    """Сохранить заказчика по проверенной форме."""
    if not is_manager(actor):
        raise PermissionDenied
    client = Client.objects.select_for_update().get(pk=client_id) if client_id else Client()
    for key in ("name", "contact_name", "contact_email", "contact_phone", "is_active"):
        setattr(client, key, data[key])
    client.full_clean()
    client.save()
    return client


@transaction.atomic
def save_site_work_item(
    *,
    actor,
    site,
    work_type,
    label,
    planned_quantity,
    route=None,
    cable_type=None,
    with_underconstruction=False,
    work_item_id=None,
):
    """Создать или обновить плановую позицию, сохранив использованную идентичность."""
    if not is_manager(actor):
        raise PermissionDenied
    from features.mbg_reports.models import MbgReportRevision, MbgWorkEntry

    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    if not site.is_active or not site.group.has_ac or site.group.status != "active":
        raise ValidationError(_("Выберите действующий AC-Standort."))
    work_type = WorkType.objects.get(pk=work_type.pk)
    route = CableRoute.objects.get(pk=route.pk) if route else None
    cable_type = CableType.objects.get(pk=cable_type.pk) if cable_type else None
    if not work_type.is_active or not work_type.supports_direction("ac") or work_type.is_break:
        raise ValidationError(_("Выберите активный AC-вид работ."))
    if work_type.unit == WorkType.Unit.HOUR or work_type.calculation_rule in (
        WorkType.CalculationRule.ACTUAL,
        WorkType.CalculationRule.ZERO,
    ):
        raise ValidationError(_("Почасовые работы пока нельзя связывать с физической позицией."))
    if (route and not route.is_active) or (cable_type and not cable_type.is_active):
        raise ValidationError(_("Выберите действующие маршрут и тип кабеля."))
    if work_type.requires_route and not route:
        raise ValidationError(_("Для этой работы нужен маршрут."))
    if work_type.requires_cable_type and not cable_type:
        raise ValidationError(_("Для этой работы нужен тип кабеля."))
    if not work_type.requires_cable_type and cable_type:
        raise ValidationError(_("Тип кабеля доступен только для прокладки."))
    if not label.strip():
        raise ValidationError(_("Укажите название позиции."))
    try:
        planned_quantity = Decimal(str(planned_quantity))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(_("Укажите корректный плановый объём.")) from exc
    if not planned_quantity.is_finite() or planned_quantity <= 0:
        raise ValidationError(_("Плановый объём должен быть больше нуля."))

    item = (
        SiteWorkItem.objects.select_for_update().get(pk=work_item_id, site=site)
        if work_item_id
        else SiteWorkItem(site=site)
    )
    identity = (work_type.pk, getattr(route, "pk", None), getattr(cable_type, "pk", None), with_underconstruction)
    if item.pk:
        previous = (item.work_type_id, item.route_id, item.cable_type_id, item.with_underconstruction)
        if identity != previous:
            used_now = MbgWorkEntry.objects.filter(work_item=item).exists()
            used_in_revision = any(
                entry.get("work_item_id") == item.pk
                for snapshot in MbgReportRevision.objects.filter(report__site=site).values_list("snapshot", flat=True)
                for entry in snapshot.get("entries", [])
            )
            if used_now or used_in_revision:
                raise ValidationError(_("Нельзя менять параметры позиции, уже использованной в отчёте."))
    before = work_item_snapshot(item) if item.pk else {}
    item.work_type = work_type
    item.route = route
    item.cable_type = cable_type
    item.with_underconstruction = with_underconstruction
    item.label = label.strip()
    item.planned_quantity = planned_quantity
    if not item.pk or identity != previous:
        item.unit_snapshot = cable_type.unit_display if cable_type else work_type.get_unit_display()
    item.full_clean()
    item.save()
    after = work_item_snapshot(item)
    if before != after:
        record_event(
            actor=actor,
            action="work_item_updated" if before else "work_item_created",
            target=item,
            before=before,
            after=after,
        )
    return item


@transaction.atomic
def apply_typical_site_plan(*, actor, site, config: TypicalPlanConfig, selected):
    """Один раз создать проверенные позиции типового плана на пустом Standort."""
    if not is_manager(actor):
        raise PermissionDenied
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    if SiteWorkItem.objects.filter(site=site).exists():
        raise ValidationError(_("Для Standort уже есть план. Измените его существующие позиции."))
    if not site.is_active or not site.group.has_ac or site.group.status != "active":
        raise ValidationError(_("Выберите действующий AC-Standort."))
    try:
        specifications = {spec.key: spec for spec in build_typical_plan(config)}
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if not selected or set(selected) - set(specifications):
        raise ValidationError(_("Выберите существующие позиции типового плана."))

    category_by_field = {
        "wr_power_cable_code": {"power", "heavy"},
        "data_cable_code": {"data"},
        "uv_out_power_cable_code": {"power", "heavy"},
        "nh_out_power_cable_code": {"power", "heavy"},
        "pe_cable_code": {"potential"},
        "control_cable_code": {"control"},
    }
    for field, allowed_categories in category_by_field.items():
        cable = CableType.objects.filter(code=getattr(config, field), is_active=True).first()
        if cable is None or cable.category not in allowed_categories:
            raise ValidationError(_("Выберите действующий тип кабеля для %(field)s.") % {"field": field})
    if config.pe_route_code not in {"uv-hpas-new", "other"}:
        raise ValidationError(_("Выберите путь PE-Leitung к HPAS."))

    chosen_specs = [specifications[key] for key in specifications if key in selected]
    work_codes = {spec.work_type_code for spec in chosen_specs}
    route_codes = {spec.route_code for spec in chosen_specs if spec.route_code}
    cable_codes = {spec.cable_type_code for spec in chosen_specs if spec.cable_type_code}
    works = {row.code: row for row in WorkType.objects.filter(code__in=work_codes, is_active=True)}
    routes = {row.code: row for row in CableRoute.objects.filter(code__in=route_codes, is_active=True)}
    cables = {row.code: row for row in CableType.objects.filter(code__in=cable_codes, is_active=True)}
    if set(works) != work_codes or set(routes) != route_codes or set(cables) != cable_codes:
        raise ValidationError(_("Типовой план ссылается на отсутствующий или неактивный справочник."))

    items = []
    for spec in chosen_specs:
        try:
            quantity = Decimal(str(selected[spec.key]))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(_("Укажите корректный объём каждой выбранной позиции.")) from exc
        if not quantity.is_finite() or quantity <= 0:
            raise ValidationError(_("Объём выбранной позиции должен быть больше нуля."))
        items.append(
            save_site_work_item(
                actor=actor,
                site=site,
                work_type=works[spec.work_type_code],
                label=spec.label,
                planned_quantity=quantity,
                route=routes.get(spec.route_code),
                cable_type=cables.get(spec.cable_type_code),
                with_underconstruction=spec.with_underconstruction,
            )
        )
    return tuple(items)

@transaction.atomic
def clarify_completed_work_item(*, actor, item, quantity, reason):
    """Зафиксировать явное уточнение выполненного объёма без изменения отчётов."""
    if not is_manager(actor):
        raise PermissionDenied
    item = SiteWorkItem.objects.select_for_update().get(pk=item.pk)
    if not item.is_required or not reason.strip():
        raise ValidationError('A required plan item and an explicit clarification reason are necessary.')
    try:
        quantity = Decimal(str(quantity))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError('Invalid clarified physical quantity.') from exc
    if not quantity.is_finite() or quantity <= 0:
        raise ValidationError('The clarified physical quantity must be positive.')
    before = work_item_snapshot(item)
    item.clarified_completed_quantity = quantity
    item.completion_clarification_reason = reason.strip()
    item.completion_confirmed_at = timezone.now()
    item.completion_confirmed_by = actor
    item.full_clean()
    item.save(update_fields=['clarified_completed_quantity', 'completion_clarification_reason',
                             'completion_confirmed_at', 'completion_confirmed_by'])
    after = work_item_snapshot(item)
    if before != after:
        record_event(actor=actor, action='work_completion_clarified', target=item,
                     before=before, after=after, reason=reason.strip())
    return item
