"""Read model DTOs for accepted MBG reporting and settlement/acceptance circuits."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from features.mbg_reports.selectors import GroupPositionRow


@dataclass(frozen=True)
class AcceptedEntryFact:
    """Детерминированный срез одной рабочей строки принятого отчёта."""

    description: str
    work_type_code: str
    unit: str
    quantity: Decimal | None
    actual_person_hours: Decimal
    amount: Decimal
    starts_at: str
    ends_at: str
    participant_names: tuple[str, ...]
    is_break: bool
    work_item_id: int | None
    route: str
    cable_type: str
    internal_only: bool = False
    entry_index: int = 0


@dataclass(frozen=True)
class AcceptedDayFact:
    """Срез одного принятого дня объекта из неизменяемой ревизии."""

    report_id: int
    version: int
    work_date: date
    iso_year: int
    iso_week: int
    site_id: int
    site_name: str
    address: str
    project_number: str
    group_name: str
    workforce_names: tuple[str, ...]
    entries: tuple[AcceptedEntryFact, ...]
    total_hours: Decimal
    total_material_amount: Decimal


@dataclass(frozen=True)
class CuratorReviewFact:
    """Состояние проверки куратором: без выдуманной приёмки."""

    status: str
    freigabe: str
    note: str
    date: str


@dataclass(frozen=True)
class SiteReportingSummary:
    """Агрегированная сводка одного Standort для отчётов и синхронизации."""

    site_id: int
    site_name: str
    address: str
    project_number: str
    group_name: str
    construction_status: str
    is_completed: bool
    day_facts: tuple[AcceptedDayFact, ...]
    curator_review: CuratorReviewFact
    position_rows: tuple["GroupPositionRow", ...]
    total_hours: Decimal
    total_material_amount: Decimal
    unique_employee_names: tuple[str, ...]
    work_days_count: int
    is_paid: bool = False


@dataclass(frozen=True)
class AcceptedReportingDataset:
    """Единый контракт набора принятых отчётов без доступа к черновикам и живым строкам."""

    periods: tuple[tuple[int, int], ...]
    sites_by_period: dict[tuple[int, int], dict[int, SiteReportingSummary]]
    all_sites: dict[int, SiteReportingSummary]
    excluded_report_ids: tuple[int, ...]
