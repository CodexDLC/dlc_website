"""Детерминированные расчёты позиции работ MBG."""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from features.internal_time.calculations import duration_minutes


@dataclass(frozen=True)
class PositionTotals:
    """Снимок норматива, фактического времени и предварительной суммы."""

    normative_person_hours: Decimal
    actual_person_hours: Decimal
    amount: Decimal


def calculate_position(
    *,
    work_type,
    starts_at: time,
    ends_at: time,
    participant_count: int,
    quantity: Decimal,
    cable_type=None,
    standard_connections: int = 0,
    heavy_connections: int = 0,
    with_underconstruction: bool = False,
) -> PositionTotals:
    """Рассчитать позицию без обращения к базе и интерфейсу."""
    quantity = Decimal(quantity)
    actual = Decimal(duration_minutes(starts_at, ends_at)) * participant_count / Decimal(60)
    if work_type.is_break:
        return PositionTotals(Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    rule = work_type.calculation_rule
    if rule == work_type.CalculationRule.CABLE:
        normative = cable_type.normative_hours_per_ten_meters * quantity
    elif rule == work_type.CalculationRule.CONNECTION:
        normative = (
            work_type.normative_hours * quantity
            + Decimal("0.25") * standard_connections
            + Decimal("0.75") * heavy_connections
        )
    elif rule in (work_type.CalculationRule.ACTUAL, work_type.CalculationRule.ZERO):
        normative = actual
    else:
        normative = work_type.normative_hours * quantity
        if with_underconstruction:
            normative += work_type.underconstruction_hours * quantity

    price_mode = work_type.price_mode
    if price_mode == work_type.PriceMode.PER_UNIT:
        unit_price = (
            cable_type.unit_price_per_ten_meters
            if rule == work_type.CalculationRule.CABLE and cable_type.unit_price_per_ten_meters
            else work_type.unit_price
        )
        amount = unit_price * quantity
        if with_underconstruction and getattr(work_type, "underconstruction_hours", 0):
            amount += (work_type.underconstruction_hours * Decimal("35.00")) * quantity
        if rule == work_type.CalculationRule.CONNECTION:
            amount += Decimal("20.00") * standard_connections + Decimal("30.00") * heavy_connections
    elif price_mode == work_type.PriceMode.PER_NORM_HOUR:
        amount = work_type.unit_price * normative
    elif price_mode == work_type.PriceMode.ACTUAL_HOURLY:
        amount = work_type.unit_price * actual
    else:
        amount = Decimal("0")
    return PositionTotals(
        normative_person_hours=normative.quantize(Decimal("0.01")),
        actual_person_hours=actual.quantize(Decimal("0.01")),
        amount=amount.quantize(Decimal("0.01")),
    )
