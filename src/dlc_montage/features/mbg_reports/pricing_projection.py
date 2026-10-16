"""Политика согласованной стоимости для принятых снимков MBG.

Согласно актуальным требованиям:
- Все новые финансовые цены/ставки/суммы MBG строго равны 0.00 € (включая доставку и почасовые позиции);
- Физические объёмы (quantity) и фактические часы сохраняются без изменений;
- Неизвестное количество остаётся None (не подменяется нулём или единицей).
"""

from dataclasses import dataclass
from decimal import Decimal

from .completion_projection import CompletionRow

AGREED_HOURLY_CODES = frozenset({"licht", "material", "sonstige"})
AGREED_HOURLY_RATE = Decimal("0.00")
AGREED_FLAT_RATES = {
    "material-delivery": Decimal("0.00"),
}


@dataclass(frozen=True)
class PriceResult:
    state: str
    unit_price: Decimal | None
    amount: Decimal | None


def price_completion_row(row: CompletionRow) -> PriceResult:
    """Вернуть финансовую оценку строки с нулевыми ставками по утверждённому регламенту."""
    if row.kind == "photo_package":
        return PriceResult("free", Decimal("0.00"), Decimal("0.00"))
    if row.kind == "hourly" and all(source["calculation_rule"] == "zero" for source in row.sources):
        return PriceResult("free", Decimal("0.00"), Decimal("0.00"))
    if row.kind == "flat" and all(source["work_type_code"] in AGREED_FLAT_RATES for source in row.sources):
        if row.quantity is None:
            return PriceResult("agreed_flat", Decimal("0.00"), None)
        return PriceResult("agreed_flat", Decimal("0.00"), Decimal("0.00"))
    if row.kind == "hourly" and all(
        source["calculation_rule"] == "actual" and source["work_type_code"] in AGREED_HOURLY_CODES
        for source in row.sources
    ):
        return PriceResult("agreed_hourly", Decimal("0.00"), Decimal("0.00"))

    if row.quantity is None and row.kind != "hourly":
        return PriceResult("unagreed", Decimal("0.00"), None)

    return PriceResult("unagreed", Decimal("0.00"), Decimal("0.00"))
