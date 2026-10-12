"""Pure validation of report rows, independent of storage and UI language."""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal, InvalidOperation


class ReportValidationError(ValueError):
    """Stable error code translated by the calling UI adapter."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class EntryInput:
    """Only values needed by the shared entry rules."""

    starts_at: time
    ends_at: time
    participant_ids: frozenset
    quantity: Decimal
    requires_route: bool = False
    has_route: bool = False
    requires_cable_type: bool = False
    has_cable_type: bool = False


def validate_report_context(entry_count, workforce_ids):
    """Validate report-level limits before preparing any rows."""
    if not 1 <= entry_count <= 100:
        raise ReportValidationError("entries_count")
    if not workforce_ids:
        raise ReportValidationError("workforce")


def validate_report_entries(entries, *, workforce_ids):
    """Validate a complete batch; database cross-report conflicts stay in adapters."""
    workforce_ids = set(workforce_ids)
    validate_report_context(len(entries), workforce_ids)
    for index, row in enumerate(entries):
        start, end = row.starts_at, row.ends_at
        if start >= end or start.second or end.second or start.minute % 15 or end.minute % 15:
            raise ReportValidationError("time_grid")
        participants = set(row.participant_ids)
        if not participants:
            raise ReportValidationError("participants")
        if participants - workforce_ids:
            raise ReportValidationError("participants_outside_workforce")
        try:
            quantity = Decimal(str(row.quantity))
        except (InvalidOperation, ValueError):
            raise ReportValidationError("quantity") from None
        if not quantity.is_finite() or quantity <= 0:
            raise ReportValidationError("quantity")
        if row.requires_route and not row.has_route:
            raise ReportValidationError("route_required")
        if row.requires_cable_type and not row.has_cable_type:
            raise ReportValidationError("cable_required")
        if not row.requires_cable_type and row.has_cable_type:
            raise ReportValidationError("cable_unexpected")
        for other in entries[:index]:
            if participants & set(other.participant_ids) and start < other.ends_at and end > other.starts_at:
                raise ReportValidationError("overlap")
