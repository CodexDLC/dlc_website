# ruff: noqa: RUF002
"""Сервисы управления оплатами отдельных Standorte (AcObject).

Дисциплина:
- Write-path только через атомарные транзакции с блокировкой select_for_update();
- Строгая проверка прав менеджера (is_manager);
- Каждое изменение фиксируется в CustomerAuditEvent по принятой конвенции аудита;
- Оплата является сугубо финансовым атрибутом Standort и никогда не меняет статус готовности (completed)
  и не изменяет снимки принятых отчётов MBG;
- Управление независимо per Standort (никогда на уровне группы / Anlage).
"""

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from loguru import logger

from features.customer_portal.audit import record_event
from features.mbg_reports.policies import can_export_reports
from features.projects.models import AcObject


def _payment_snapshot(site: AcObject) -> dict[str, Any]:
    """Снимок платежных полей Standort для неизменяемого аудита."""
    return {
        "site_id": site.pk,
        "is_paid": site.is_paid,
        "paid_at": site.paid_at.isoformat() if site.paid_at else None,
        "paid_by_id": site.paid_by_id,
        "payment_note": site.payment_note,
    }


@transaction.atomic
def mark_site_paid(
    *,
    actor,
    site_id: int,
    paid_at=None,
    note: str = "",
    reason: str = "",
) -> AcObject:
    """Авторизованно отметить факт оплаты Standort.

    Сохраняет статус готовности объекта (completed / in_progress) неизменным.
    Доступно строго администратору с правом экспорта финансовых отчетов.
    Идемпотентный вызов без изменений не дублирует запись аудита.
    """
    if not can_export_reports(actor):
        raise PermissionDenied("Nur Administratoren dürfen Zahlungen buchen.")

    clean_note = note.strip()
    if len(clean_note) > 255:
        raise ValidationError("Die Zahlungsnotiz darf maximal 255 Zeichen lang sein.")

    payment_time = paid_at or timezone.now()
    if paid_at is not None and payment_time > timezone.now() + timezone.timedelta(days=1):
        raise ValidationError("Das Zahlungsdatum darf nicht in der Zukunft liegen.")

    site = AcObject.objects.select_for_update().select_related("group", "group__client").get(pk=site_id)

    # Идемпотентность: если объект уже оплачен с теми же параметрами, аудит не дублируется
    if site.is_paid and site.payment_note == clean_note and (paid_at is None or site.paid_at == payment_time):
        return site

    before = _payment_snapshot(site)

    site.is_paid = True
    site.paid_at = payment_time
    site.paid_by = actor
    site.payment_note = clean_note
    site.save(update_fields=["is_paid", "paid_at", "paid_by", "payment_note"])

    after = _payment_snapshot(site)
    record_event(
        actor=actor,
        action="site_payment_marked",
        target=site,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    logger.info(
        "Standort payment marked: site_id={}, actor_id={}, paid_at={}",
        site.pk,
        actor.pk,
        payment_time,
    )
    return site


@transaction.atomic
def unmark_site_paid(
    *,
    actor,
    site_id: int,
    reason: str = "",
) -> AcObject:
    """Авторизованно снять отметку оплаты Standort (возврат к Offen).

    Сохраняет статус готовности объекта неизменным.
    Доступно строго администратору с правом экспорта финансовых отчетов.
    Идемпотентный вызов без изменений не дублирует запись аудита.
    """
    if not can_export_reports(actor):
        raise PermissionDenied("Nur Administratoren dürfen Zahlungen stornieren.")

    site = AcObject.objects.select_for_update().select_related("group", "group__client").get(pk=site_id)

    # Идемпотентность: если объект уже не оплачен, аудит не дублируется
    if not site.is_paid:
        return site

    before = _payment_snapshot(site)

    site.is_paid = False
    site.paid_at = None
    site.paid_by = None
    site.payment_note = ""
    site.save(update_fields=["is_paid", "paid_at", "paid_by", "payment_note"])

    after = _payment_snapshot(site)
    record_event(
        actor=actor,
        action="site_payment_unmarked",
        target=site,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    logger.info(
        "Standort payment unmarked: site_id={}, actor_id={}",
        site.pk,
        actor.pk,
    )
    return site


@transaction.atomic
def set_site_payment_status(
    *,
    actor,
    site_id: int,
    is_paid: bool,
    paid_at=None,
    note: str = "",
    reason: str = "",
) -> AcObject:
    """Универсальный переключатель статуса оплаты с полным аудитом."""
    if is_paid:
        return mark_site_paid(actor=actor, site_id=site_id, paid_at=paid_at, note=note, reason=reason)
    return unmark_site_paid(actor=actor, site_id=site_id, reason=reason)
