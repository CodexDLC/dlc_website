"""Чистый рецепт редактируемого типового AC-плана Standort."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TypicalPlanConfig:
    inverter_count: int = 1
    include_nh: bool = True
    include_nh_hv: bool = False
    wr_underconstruction: bool = False
    uv_underconstruction: bool = False
    nh_underconstruction: bool = False
    include_control: bool = False
    include_trays: bool = False
    include_hpas_connection: bool = False
    wr_power_cable_code: str = "power-5x16"
    data_cable_code: str = "data"
    uv_out_power_cable_code: str = "power-5x16"
    nh_out_power_cable_code: str = "power-5x35"
    pe_cable_code: str = "pe-1x16"
    control_cable_code: str = "control-7x1-5"
    pe_route_code: str = "uv-hpas-new"


@dataclass(frozen=True)
class TypicalWorkSpec:
    key: str
    label: str
    work_type_code: str
    route_code: str | None = None
    cable_type_code: str | None = None
    with_underconstruction: bool = False
    planned_quantity: Decimal = Decimal("1")


def build_typical_plan(config: TypicalPlanConfig) -> tuple[TypicalWorkSpec, ...]:
    """Создать отдельные физические позиции из выбранной конфигурации."""
    if not isinstance(config.inverter_count, int) or not 1 <= config.inverter_count <= 20:
        raise ValueError("Количество Wechselrichter должно быть от 1 до 20.")
    specs = [
        TypicalWorkSpec("uv-mount", "Montage UV-PV", "uv-montage", with_underconstruction=config.uv_underconstruction),
        TypicalWorkSpec("uv-connect", "Anschluss UV-PV", "uv-anschluss"),
    ]
    for number in range(1, config.inverter_count + 1):
        specs.extend((
            TypicalWorkSpec(
                f"wr-{number}-mount", f"Montage Wechselrichter {number}", "wr-montage",
                with_underconstruction=config.wr_underconstruction,
            ),
            TypicalWorkSpec(f"wr-{number}-connect", f"Anschluss Wechselrichter {number}", "wr-anschluss"),
            TypicalWorkSpec(
                f"wr-{number}-power", f"Leistungskabel WR {number} → UV-PV", "cable-laying",
                "wr-uv", config.wr_power_cable_code,
            ),
            TypicalWorkSpec(
                f"wr-{number}-data", f"Datenleitung WR {number} → UV-PV", "cable-laying",
                "wr-uv", config.data_cable_code,
            ),
        ))
    outgoing = "uv-nh-new" if config.include_nh else "uv-hv"
    outgoing_label = "neuer NH-Verteiler" if config.include_nh else "HV"
    specs.extend((
        TypicalWorkSpec(
            "uv-out-power", f"Leistungskabel UV-PV → {outgoing_label}", "cable-laying",
            outgoing, config.uv_out_power_cable_code,
        ),
        TypicalWorkSpec(
            "uv-pe", "PE-Leitung UV-PV → HPAS", "cable-laying", config.pe_route_code, config.pe_cable_code,
        ),
    ))
    if config.include_nh:
        specs.extend((
            TypicalWorkSpec(
                "nh-mount", "Montage NH-Verteiler", "nh-montage",
                with_underconstruction=config.nh_underconstruction,
            ),
            TypicalWorkSpec("nh-connect", "Anschluss NH-Verteiler", "nh-anschluss"),
        ))
        if config.include_nh_hv:
            specs.append(TypicalWorkSpec(
                "nh-out-power", "Leistungskabel NH-Verteiler → HV", "cable-laying",
                "nh-new-hv", config.nh_out_power_cable_code,
            ))
    if config.include_control:
        specs.append(TypicalWorkSpec(
            "control-line", "Steuerleitung UV-PV → Außenschlüsselschalter", "cable-laying",
            "uv-key-switch", config.control_cable_code,
        ))
    if config.include_hpas_connection:
        specs.append(TypicalWorkSpec("hpas-connect", "Anschluss an HPAS", "hpas-anschluss"))
    if config.include_trays:
        specs.extend((
            TypicalWorkSpec("tray-wr-uv", "Kabeltrasse WR → UV-PV", "cable-tray", "wr-uv"),
            TypicalWorkSpec("tray-uv-out", f"Kabeltrasse UV-PV → {outgoing_label}", "cable-tray", outgoing),
        ))
        if config.include_nh and config.include_nh_hv:
            specs.append(TypicalWorkSpec("tray-nh-hv", "Kabeltrasse NH-Verteiler → HV", "cable-tray", "nh-new-hv"))
    return tuple(specs)
