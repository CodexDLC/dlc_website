"""Атомарные клиентские изменения без побочных финансовых эффектов."""

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _

from features.internal_time.policies import is_manager
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.project_media.models import ProjectFile
from features.project_media.services import validate_upload
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.services import save_site_work_item
from features.projects.typical_plan import TypicalPlanConfig, build_typical_plan
from features.work_catalog.models import CableRoute, CableType, WorkType

from .audit import group_snapshot, record_event
from .models import ClientMembership, PlanProposal, SiteReview
from .policies import membership_for, require_customer_group, require_customer_site


@transaction.atomic
def change_account_password(*, actor, password):
    """Change only the authorized actor's password after form validation."""
    if not actor.is_active or (not is_manager(actor) and membership_for(actor) is None):
        raise PermissionDenied
    validate_password(password, actor)
    actor.set_password(password)
    actor.save(update_fields=["password"])
    return actor


def _audit(*, actor, action, target, before=None, after=None, reason=""):
    """Записать минимальный предметный снимок без цен и персональных часов."""
    return record_event(actor=actor, action=action, target=target, before=before, after=after, reason=reason)


@transaction.atomic
def grant_membership(*, actor, user, client, can_manage_projects=False, is_active=True):
    """Назначить единственного заказчика только решением менеджера."""
    if not is_manager(actor):
        raise PermissionDenied
    if not client.is_active or not user.is_active or is_manager(user):
        raise ValidationError(_("Выберите активного заказчика и обычного активного пользователя."))
    existing = ClientMembership.objects.select_for_update().filter(user=user).first()
    if (
        existing
        and existing.client_id == client.pk
        and existing.is_active == is_active
        and existing.can_manage_projects == can_manage_projects
    ):
        return existing
    before = (
        {
            "client_id": existing.client_id,
            "active": existing.is_active,
            "can_manage_projects": existing.can_manage_projects,
        }
        if existing
        else {}
    )
    previous_client = existing.client if existing and existing.client_id != client.pk else None
    membership = existing or ClientMembership(user=user)
    membership.client = client
    membership.is_active = is_active
    membership.can_manage_projects = can_manage_projects
    membership.granted_by = actor
    membership.full_clean()
    membership.save()
    after = {
        "user_id": user.pk,
        "client_id": client.pk,
        "active": is_active,
        "can_manage_projects": can_manage_projects,
    }
    _audit(
        actor=actor,
        action="membership_saved",
        target=membership,
        before=before,
        after=after,
    )
    if previous_client:
        record_event(
            actor=actor,
            action="membership_saved",
            target=membership,
            before=before,
            after=after,
            client=previous_client,
        )
    return membership


_group_snapshot = group_snapshot


@transaction.atomic
def save_customer_group(*, actor, data, group_id=None, reason=""):
    """Создать/изменить только публичные поля Anlage в своей компании."""
    membership = membership_for(actor)
    if not is_manager(actor) and (membership is None or not membership.can_manage_projects):
        raise PermissionDenied
    if group_id:
        group = ProjectGroup.objects.select_for_update().get(pk=group_id)
        require_customer_group(actor, group, manage=True)
        before = _group_snapshot(group)
        started = (
            group.ac_objects.exclude(status="not_started").exists()
            or MbgDailyReport.objects.filter(site__group=group, status="accepted").exists()
        )
        if started and not reason.strip():
            raise ValidationError(_("Объясните изменение уже начатой Anlage."))
    else:
        if is_manager(actor):
            raise ValidationError(_("Администратор создаёт Anlage через внутренний редактор."))
        group = ProjectGroup(client=membership.client)
        before = {}
    allowed = {
        "name",
        "address",
        "additional_addresses",
        "capacity_kw",
        "maps_url",
        "starts_on",
        "ends_on",
        "has_ac",
        "has_dc",
    }
    if set(data) - allowed:
        raise PermissionDenied
    for key, value in data.items():
        setattr(group, key, value)
    group.full_clean()
    group.save()
    _audit(
        actor=actor,
        action="group_updated" if group_id else "group_created",
        target=group,
        before=before,
        after=_group_snapshot(group),
        reason=reason.strip(),
    )
    return group


@transaction.atomic
def save_customer_site(*, actor, group, data, site_id=None, reason=""):
    """Создать/изменить адрес Standort без изменения готовности и исполнителей."""
    group = ProjectGroup.objects.select_for_update().get(pk=group.pk)
    require_customer_group(actor, group, manage=True)
    if group.status != "active" or not group.has_ac:
        raise ValidationError(_("Требуется активная AC-Anlage."))
    site = AcObject.objects.select_for_update().get(pk=site_id, group=group) if site_id else AcObject(group=group)
    before = {key: getattr(site, key) for key in ("name", "address", "project_number")} if site_id else {}
    if (
        site_id
        and (site.status != "not_started" or site.mbg_reports.filter(status="accepted").exists())
        and not reason.strip()
    ):
        raise ValidationError(_("Объясните изменение уже начатого Standort."))
    if set(data) - {"name", "address", "project_number"}:
        raise PermissionDenied
    for key, value in data.items():
        setattr(site, key, value)
    site.full_clean()
    site.save()
    _audit(
        actor=actor,
        action="site_updated" if site_id else "site_created",
        target=site,
        before=before,
        after={key: getattr(site, key) for key in ("name", "address", "project_number")},
        reason=reason.strip(),
    )
    return site


def _proposal_specs(config, selected):
    """Проверить положительные количества и каталог до сохранения предложения."""
    specs = {spec.key: spec for spec in build_typical_plan(config)}
    if not selected or set(selected) - set(specs):
        raise ValidationError(_("Выберите позиции типового плана."))
    payload = []
    for key, spec in specs.items():
        if key not in selected:
            continue
        try:
            amount = Decimal(str(selected[key]))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(_("Укажите положительный плановый объём.")) from exc
        if not amount.is_finite() or amount <= 0:
            raise ValidationError(_("Укажите положительный плановый объём."))
        if not WorkType.objects.filter(code=spec.work_type_code, is_active=True).exists():
            raise ValidationError(_("Вид работы отсутствует в каталоге."))
        if spec.route_code and not CableRoute.objects.filter(code=spec.route_code, is_active=True).exists():
            raise ValidationError(_("Путь отсутствует в каталоге."))
        if spec.cable_type_code:
            cable = CableType.objects.filter(code=spec.cable_type_code, is_active=True).first()
            if cable is None or cable.category not in _allowed_cable_categories(key):
                raise ValidationError(_("Тип кабеля отсутствует или не подходит к позиции."))
        payload.append({**asdict(spec), "planned_quantity": str(amount)})
    return payload


def _allowed_cable_categories(key):
    """Зафиксировать роль кабеля независимо от произвольного кода в форме."""
    if key.endswith("-power"):
        return {"power", "heavy"}
    if key.endswith("-data"):
        return {"data"}
    if key == "uv-pe":
        return {"potential"}
    if key == "control-line":
        return {"control"}
    if key == "manual":
        return {"power", "heavy", "data", "potential", "control"}
    return set()


@transaction.atomic
def propose_plan(*, actor, site, selected, config=None):
    """Предложить новые позиции, не меняя текущий план и принятые отчёты."""
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    require_customer_site(actor, site, manage=True)
    if site.group.status != "active" or not site.is_active or not site.group.has_ac:
        raise ValidationError(_("Требуется активный AC-Standort."))
    if PlanProposal.objects.filter(site=site, status="pending").exists():
        raise ValidationError(_("Предложение по этому Standort уже ожидает решения."))
    payload = _proposal_specs(config or TypicalPlanConfig(), selected)
    proposal = PlanProposal.objects.create(site=site, proposed_by=actor, payload=payload)
    _audit(
        actor=actor,
        action="plan_proposed",
        target=proposal,
        after={
            "site_id": site.pk,
            "positions": payload,
        },
    )
    return proposal


@transaction.atomic
def propose_manual_item(
    *, actor, site, work_type, label, planned_quantity, route=None, cable_type=None, with_underconstruction=False
):
    """Предложить одну отдельную работу из каталога; позиция появится лишь после решения администратора."""
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    require_customer_site(actor, site, manage=True)
    if site.group.status != "active" or not site.is_active or not site.group.has_ac:
        raise ValidationError(_("Требуется активный AC-Standort."))
    if PlanProposal.objects.filter(site=site, status="pending").exists():
        raise ValidationError(_("Предложение по этому Standort уже ожидает решения."))
    work_type = WorkType.objects.filter(pk=getattr(work_type, "pk", None), is_active=True).first()
    if work_type is None or not work_type.supports_direction("ac") or work_type.is_break:
        raise ValidationError(_("Выберите активный AC-вид работ из каталога."))
    if work_type.unit == WorkType.Unit.HOUR or work_type.calculation_rule in (
        WorkType.CalculationRule.ACTUAL,
        WorkType.CalculationRule.ZERO,
    ):
        raise ValidationError(_("Почасовые работы нельзя предлагать как физическую позицию."))
    route = CableRoute.objects.filter(pk=route.pk, is_active=True).first() if route else None
    cable_type = CableType.objects.filter(pk=cable_type.pk, is_active=True).first() if cable_type else None
    if work_type.requires_route and route is None:
        raise ValidationError(_("Для этой работы нужен маршрут."))
    if work_type.requires_cable_type != (cable_type is not None):
        raise ValidationError(_("Тип кабеля нужен только для прокладки кабеля."))
    if cable_type and cable_type.category not in _allowed_cable_categories("manual"):
        raise ValidationError(_("Тип кабеля не подходит к позиции."))
    label = (label or "").strip()
    if not label or len(label) > SiteWorkItem._meta.get_field("label").max_length:
        raise ValidationError(_("Укажите название позиции."))
    if SiteWorkItem.objects.filter(site=site, label=label).exists():
        raise ValidationError(_("В плане уже есть такая позиция."))
    try:
        amount = Decimal(str(planned_quantity))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(_("Укажите положительный плановый объём.")) from exc
    if not amount.is_finite() or amount <= 0:
        raise ValidationError(_("Укажите положительный плановый объём."))
    row = {
        "key": "manual",
        "label": label,
        "work_type_code": work_type.code,
        "route_code": route.code if route else "",
        "cable_type_code": cable_type.code if cable_type else "",
        "with_underconstruction": bool(with_underconstruction),
        "planned_quantity": str(amount),
    }
    proposal = PlanProposal.objects.create(site=site, proposed_by=actor, payload=[row])
    _audit(actor=actor, action="plan_proposed", target=proposal, after={"site_id": site.pk, "positions": [row]})
    return proposal


@transaction.atomic
def review_plan(*, actor, proposal, approve, reason=""):
    """Принять новые позиции однократно, не перезаписывая существующие."""
    if not is_manager(actor):
        raise PermissionDenied
    proposal = PlanProposal.objects.select_for_update().select_related("site__group").get(pk=proposal.pk)
    if proposal.status != "pending":
        raise ValidationError(_("Предложение уже рассмотрено."))
    AcObject.objects.select_for_update().get(pk=proposal.site_id)
    if not reason.strip():
        raise ValidationError(_("Укажите причину решения."))
    created_ids = []
    if approve:
        existing = set(SiteWorkItem.objects.filter(site=proposal.site).values_list("label", flat=True))
        if any(row["label"] in existing for row in proposal.payload):
            raise ValidationError(_("В плане уже есть такая позиция; сначала разберите дубликат."))
        if len({row["label"] for row in proposal.payload}) != len(proposal.payload):
            raise ValidationError(_("В предложении повторяются позиции."))
        for row in proposal.payload:
            work_type = WorkType.objects.get(code=row["work_type_code"], is_active=True)
            route = CableRoute.objects.get(code=row["route_code"], is_active=True) if row["route_code"] else None
            cable_type = (
                CableType.objects.get(code=row["cable_type_code"], is_active=True) if row["cable_type_code"] else None
            )
            if cable_type and cable_type.category not in _allowed_cable_categories(row["key"]):
                raise ValidationError(_("Тип кабеля больше не подходит к плану."))
            item = save_site_work_item(
                actor=actor,
                site=proposal.site,
                work_type=work_type,
                label=row["label"],
                planned_quantity=Decimal(row["planned_quantity"]),
                route=route,
                cable_type=cable_type,
                with_underconstruction=row["with_underconstruction"],
            )
            created_ids.append(item.pk)
    proposal.status = "approved" if approve else "rejected"
    proposal.decided_by = actor
    proposal.decision_reason = reason.strip()
    proposal.decided_at = timezone.now()
    proposal.save(update_fields=["status", "decided_by", "decision_reason", "decided_at"])
    _audit(
        actor=actor,
        action="plan_reviewed",
        target=proposal,
        before={"status": "pending"},
        after={"status": proposal.status, "created_work_item_ids": created_ids},
        reason=reason.strip(),
    )
    return proposal


def accepted_snapshot_digest(site):
    """Хешировать только актуальные принятые версии отчётов объекта."""
    reports = list(MbgDailyReport.objects.filter(site=site, status="accepted").order_by("pk"))
    revisions = {
        (row.report_id, row.version): row.snapshot
        for row in MbgReportRevision.objects.filter(report__in=reports, version=F("report__version"))
    }
    data = []
    for report in reports:
        snapshot = revisions.get((report.pk, report.version))
        if not snapshot or snapshot.get("status") != "accepted":
            raise ValidationError(_("У принятого отчёта отсутствует текущий подтверждённый снимок."))
        data.append([report.pk, report.version, snapshot])
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


@transaction.atomic
def submit_for_review(*, actor, site):
    """Администратор отправляет неизменный срез выполненных работ клиенту."""
    if not is_manager(actor):
        raise PermissionDenied
    site = AcObject.objects.select_for_update().get(pk=site.pk)
    if site.group.client_id is None or not site.group.client.is_active:
        raise ValidationError(_("Для проверки требуется активный заказчик Anlage."))
    if not MbgDailyReport.objects.filter(site=site, status="accepted").exists():
        raise ValidationError(_("Для проверки требуются принятые дневные работы."))
    digest = accepted_snapshot_digest(site)
    review, _created = SiteReview.objects.select_for_update().get_or_create(site=site)
    if review.status == "submitted" and review.snapshot_digest == digest:
        raise ValidationError(_("Standort уже ожидает проверки заказчика."))
    before = {"status": review.status, "digest": review.snapshot_digest}
    review.status = "submitted"
    review.snapshot_digest = digest
    review.submitted_by = actor
    review.submitted_at = timezone.now()
    review.decided_by = None
    review.decided_at = None
    review.remark = ""
    review.save()
    _audit(
        actor=actor,
        action="review_submitted",
        target=review,
        before=before,
        after={"status": review.status, "digest": digest},
    )
    return review


@transaction.atomic
def decide_review(*, actor, site, accept, reason=""):
    """Клиент принимает без замечаний или возвращает с обязательной причиной."""
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    if is_manager(actor):
        raise PermissionDenied
    require_customer_site(actor, site)
    review = SiteReview.objects.select_for_update().get(site=site)
    if review.status != "submitted":
        raise ValidationError(_("Нет открытой проверки."))
    if not accept and not reason.strip():
        raise ValidationError(_("Укажите замечание для возврата."))
    if review.snapshot_digest != accepted_snapshot_digest(site):
        raise ValidationError(_("Принятые работы изменились. Попросите отправить объект на проверку заново."))
    review.status = "accepted" if accept else "returned"
    review.decided_by = actor
    review.decided_at = timezone.now()
    review.remark = "" if accept else reason.strip()
    review.save(update_fields=["status", "decided_by", "decided_at", "remark"])
    _audit(
        actor=actor,
        action="review_decided",
        target=review,
        before={"status": "submitted"},
        after={"status": review.status, "digest": review.snapshot_digest},
        reason=review.remark,
    )
    return review


def upload_customer_pdf(*, actor, group, upload, site=None, caption=""):
    """Сохранить проверенный PDF в приватном хранилище с явной видимостью клиенту."""
    require_customer_group(actor, group, manage=True)
    if site and site.group_id != group.pk:
        raise ValidationError(_("Standort не принадлежит Anlage."))
    if Path(upload.name).suffix.lower() != ".pdf":
        raise ValidationError(_("Для документов заказчика разрешён только PDF."))
    content_type = validate_upload(upload, "document")
    item = ProjectFile(
        group=group,
        site=site,
        kind="document",
        caption=caption,
        original_name=Path(upload.name).name,
        content_type=content_type,
        size=upload.size,
        uploaded_by=actor,
        customer_visible=True,
    )
    item.file = upload
    item.full_clean()
    try:
        with transaction.atomic():
            item.save()
            _audit(
                actor=actor,
                action="document_uploaded",
                target=item,
                after={"group_id": group.pk, "site_id": site.pk if site else None, "name": item.original_name},
            )
    except Exception:
        if item.file and item.file._committed:
            item.file.storage.delete(item.file.name)
        raise
    return item


@transaction.atomic
def set_customer_file_visibility(*, actor, item, visible, reason):
    """Менеджер явно открывает PDF конкретной Anlage заказчику."""
    if not is_manager(actor):
        raise PermissionDenied
    if not reason.strip():
        raise ValidationError(_("Укажите причину изменения доступа к документу."))
    item = ProjectFile.objects.select_for_update().get(pk=item.pk)
    if item.content_type != "application/pdf" or item.kind != "document":
        raise ValidationError(_("Открывать заказчику можно только PDF-документ."))
    before = item.customer_visible
    item.customer_visible = bool(visible)
    item.save(update_fields=["customer_visible"])
    _audit(
        actor=actor,
        action="document_visibility",
        target=item,
        before={"customer_visible": before},
        after={"customer_visible": item.customer_visible},
        reason=reason.strip(),
    )
    return item
