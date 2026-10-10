"""Доменный фасад взаиморасчётов и платежного статуса Standorte (AcObject).

Объединяет read-path селекторы и write-path транзакционные сервисы:
- settlement_services: авторизованные мутации статуса оплаты с аудитом;
- settlement_selectors: выборка для счетов (исключение оплаченных) и исторического регистра (сохранение оплаченных).
"""

from .settlement_selectors import (
    filter_sites_for_historical_ledger,
    filter_sites_for_invoice,
    get_site_payment_status,
    get_sites_payment_map,
)
from .settlement_services import (
    mark_site_paid,
    set_site_payment_status,
    unmark_site_paid,
)

__all__ = [
    "filter_sites_for_historical_ledger",
    "filter_sites_for_invoice",
    "get_site_payment_status",
    "get_sites_payment_map",
    "mark_site_paid",
    "set_site_payment_status",
    "unmark_site_paid",
]
