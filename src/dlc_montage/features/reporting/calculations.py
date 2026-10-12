"""Детерминированные расчёты позиции работ MBG."""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from .time import duration_minutes


@dataclass(frozen=True)
class WorkCalculationSpec:
    """Values required by the calculation, without ORM identities."""

    calculation_rule: str
    price_mode: str
    normative_hours: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    underconstruction_hours: Decimal = Decimal("0")
    is_break: bool = False


@dataclass(frozen=True)
class CableCalculationSpec:
    """Cable-specific normative hours and price per ten-meter section."""

    normative_hours_per_ten_meters: Decimal
    unit_price_per_ten_meters: Decimal = Decimal("0")


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
    if rule == "cable":
        normative = cable_type.normative_hours_per_ten_meters * quantity
    elif rule == "connection":
        normative = (
            work_type.normative_hours * quantity
            + Decimal("0.25") * standard_connections
            + Decimal("0.75") * heavy_connections
        )
    elif rule in ("actual", "zero"):
        normative = actual
    else:
        normative = work_type.normative_hours * quantity
        if with_underconstruction:
            normative += work_type.underconstruction_hours * quantity

    price_mode = work_type.price_mode
    if price_mode == "per_unit":
        unit_price = (
            cable_type.unit_price_per_ten_meters
            if rule == "cable" and cable_type.unit_price_per_ten_meters
            else work_type.unit_price
        )
        amount = unit_price * quantity
        if with_underconstruction and getattr(work_type, "underconstruction_hours", 0):
            amount += (work_type.underconstruction_hours * Decimal("35.00")) * quantity
        if rule == "connection":
            amount += Decimal("20.00") * standard_connections + Decimal("30.00") * heavy_connections
    elif price_mode == "per_norm_hour":
        amount = work_type.unit_price * normative
    elif price_mode == "actual_hourly":
        amount = work_type.unit_price * actual
    else:
        amount = Decimal("0")
    return PositionTotals(
        normative_person_hours=normative.quantize(Decimal("0.01")),
        actual_person_hours=actual.quantize(Decimal("0.01")),
        amount=amount.quantize(Decimal("0.01")),
    )
