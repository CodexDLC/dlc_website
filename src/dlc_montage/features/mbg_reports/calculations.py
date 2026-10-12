"""Adapt work-catalog models to the common report calculation."""

from features.reporting.calculations import CableCalculationSpec, WorkCalculationSpec
from features.reporting.calculations import calculate_position as calculate_report_position


def calculate_position(*, work_type, cable_type=None, **kwargs):
    spec = WorkCalculationSpec(
        calculation_rule=work_type.calculation_rule,
        price_mode=work_type.price_mode,
        normative_hours=work_type.normative_hours,
        unit_price=work_type.unit_price,
        underconstruction_hours=work_type.underconstruction_hours,
        is_break=work_type.is_break,
    )
    cable = (
        None
        if cable_type is None
        else CableCalculationSpec(
            normative_hours_per_ten_meters=cable_type.normative_hours_per_ten_meters,
            unit_price_per_ten_meters=cable_type.unit_price_per_ten_meters,
        )
    )
    return calculate_report_position(work_type=spec, cable_type=cable, **kwargs)
