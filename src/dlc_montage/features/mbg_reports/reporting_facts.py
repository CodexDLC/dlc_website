"""Чистые правила вычисления фактических часов и сумм для принятых отчётов."""

from decimal import Decimal, InvalidOperation


def calc_fact_hours(entry_data: dict, workforce_count: int = 0) -> Decimal:
    """Вычислить фактические человеко-часы строки:

    - перерывы всегда 0.00 ч;
    - нулевые часы остаются 0.00 ч (никакого переопределения);
    - при отсутствии участников не изобретать 1 участника (0 участников = 0.00 ч).
    """
    if entry_data.get("is_break") or entry_data.get("work_type_code") in {"mittagspause", "pause"}:
        return Decimal("0.00")

    actual_raw = entry_data.get("actual_person_hours")
    if actual_raw is not None and str(actual_raw).strip() != "":
        try:
            return Decimal(str(actual_raw)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return Decimal("0.00")

    participants = entry_data.get("participants") or []
    p_count = len(participants) if participants else workforce_count
    if not p_count or p_count <= 0:
        return Decimal("0.00")

    minutes = entry_data.get("minutes")
    if minutes is None:
        start_str = entry_data.get("start") or entry_data.get("starts_at")
        end_str = entry_data.get("end") or entry_data.get("ends_at")
        if start_str and end_str:
            try:
                s_parts = [int(p) for p in str(start_str).split(":")[:2]]
                e_parts = [int(p) for p in str(end_str).split(":")[:2]]
                minutes = (e_parts[0] * 60 + e_parts[1]) - (s_parts[0] * 60 + s_parts[1])
            except Exception:
                minutes = 0
        else:
            minutes = 0

    if not minutes or minutes <= 0:
        return Decimal("0.00")

    return (Decimal(minutes) * Decimal(p_count) / Decimal(60)).quantize(Decimal("0.01"))


def calc_entry_amount(entry_data: dict, *, legacy_rates: bool = False) -> Decimal:
    """Рассчитать сумму позиции по утверждённым правилам:

    - Все новые финансовые суммы MBG строго равны 0.00 EUR (включая material-delivery).
    - При неизвестном количестве не подставлять 1.
    """
    if legacy_rates:
        code = entry_data.get("work_type_code") or ""
        if code == "material-delivery":
            raw_qty = entry_data.get("completed_quantity")
            if raw_qty is None:
                raw_qty = entry_data.get("quantity")
            if raw_qty is not None and str(raw_qty).strip() != "":
                try:
                    qty = Decimal(str(raw_qty))
                    return (Decimal("50.00") * qty).quantize(Decimal("0.01"))
                except (InvalidOperation, ValueError):
                    return Decimal("0.00")
            return Decimal("0.00")
        return Decimal("0.00")
    return Decimal("0.00")
