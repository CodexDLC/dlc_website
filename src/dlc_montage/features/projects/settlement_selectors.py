"""Селекторы платежного состояния и фильтрации Standorte для финансовых контуров.

Дисциплина:
- Чистые read-path запросы без мутаций базы данных;
- Контракт выборки для новых счетов (Invoice / Leistungsnachweis) по умолчанию исключает
  оплаченные объекты (is_paid=False) с явным параметром include_paid=True;
- Исторический сводный регистр (Gesamtabrechnung / Master Ledger) сохраняет все объекты,
  включая оплаченные, предоставляя их флаг оплаты;
- Предоставляет документированные интерфейсы для конечного интегратора представлений.
"""

from collections.abc import Iterable
from typing import Any

from django.db.models import QuerySet

from features.projects.models import AcObject


def get_site_payment_status(site_id: int) -> dict[str, Any]:
    """Получить детальный срез платежного статуса отдельного объекта."""
    site = AcObject.objects.select_related("paid_by").get(pk=site_id)
    return {
        "site_id": site.pk,
        "site_name": site.name,
        "is_paid": site.is_paid,
        "paid_at": site.paid_at,
        "paid_by_id": site.paid_by_id,
        "paid_by_name": str(site.paid_by) if site.paid_by else "",
        "payment_note": site.payment_note,
        "construction_status": site.status,
        "is_completed": (site.status == "completed"),
    }


def filter_sites_for_invoice(
    *,
    group_id: int | None = None,
    group_ids: Iterable[int] | None = None,
    site_ids: Iterable[int] | None = None,
    include_paid: bool = False,
    completed_only: bool = True,
) -> QuerySet[AcObject]:
    """Выбрать Standorte для формирования нового счёта / Leistungsnachweis.

    По умолчанию (include_paid=False) исключает ранее оплаченные Standorte (is_paid=False).
    По умолчанию (completed_only=True) отбирает только завершённые объекты (status='completed').
    """
    qs = AcObject.objects.filter(is_active=True).select_related("group")

    if group_id is not None:
        qs = qs.filter(group_id=group_id)
    elif group_ids is not None:
        qs = qs.filter(group_id__in=group_ids)

    if site_ids is not None:
        qs = qs.filter(pk__in=site_ids)

    if completed_only:
        qs = qs.filter(status="completed")

    if not include_paid:
        qs = qs.filter(is_paid=False)

    return qs.order_by("group__name", "name", "pk")


def filter_sites_for_historical_ledger(
    *,
    group_id: int | None = None,
    group_ids: Iterable[int] | None = None,
    site_ids: Iterable[int] | None = None,
    active_only: bool = True,
) -> QuerySet[AcObject]:
    """Выбрать Standorte для мастер-регистра / исторического сводного отчёта.

    Исторический регистр сохраняет все объекты (как оплаченные, так и открытые),
    отображая явный статус оплаты по каждому Standort.
    """
    qs = AcObject.objects.select_related("group")
    if active_only:
        qs = qs.filter(is_active=True)

    if group_id is not None:
        qs = qs.filter(group_id=group_id)
    elif group_ids is not None:
        qs = qs.filter(group_id__in=group_ids)

    if site_ids is not None:
        qs = qs.filter(pk__in=site_ids)

    return qs.order_by("group__name", "name", "pk")


def get_sites_payment_map(site_ids: Iterable[int]) -> dict[int, bool]:
    """Словарь быстрой проверки статуса оплаты: site_id -> is_paid."""
    return dict(
        AcObject.objects.filter(pk__in=site_ids).values_list("pk", "is_paid")
    )
