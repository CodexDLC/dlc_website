"""Чистые правила закрытия расчётного пакета из его физических составляющих."""

from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True)
class RequirementProgress:
    work_item_id: int
    label: str
    required_quantity: Decimal
    completed_quantity: Decimal
    is_required: bool

    @property
    def ready(self):
        return self.is_required and self.completed_quantity >= self.required_quantity


@dataclass(frozen=True)
class PackageProgress:
    package: object
    requirements: tuple[RequirementProgress, ...]
    sources: tuple[dict, ...]

    @property
    def ready(self):
        if self.package.quantity is None or not self.package.position.is_active:
            return False
        if self.requirements:
            return all(item.ready for item in self.requirements) and (
                not self.package.position.manual_only or self.package.manual_confirmed
            )
        return self.package.manual_confirmed

    @property
    def state(self):
        if self.ready:
            return "completed"
        if not self.package.position.is_active:
            return "needs_mapping"
        if self.package.quantity is None or not self.requirements:
            return "needs_mapping"
        if any(not item.is_required for item in self.requirements):
            return "needs_mapping"
        return (
            "partial" if self.sources or any(r.completed_quantity > ZERO for r in self.requirements) else "not_started"
        )

    @property
    def quantity(self):
        if (
            self.package.position.is_active
            and (not self.package.position.manual_only or self.package.manual_confirmed)
            and self.package.position.code in {"10.010", "01.0060", "01.0020", "10.020", "01.0070", "01.0050"}
            and self.requirements
            and self.package.quantity is not None
            and all(item.is_required and item.required_quantity == self.package.quantity for item in self.requirements)
        ):
            return min(self.package.quantity, *(item.completed_quantity // 1 for item in self.requirements))
        return self.package.quantity if self.ready else ZERO

    @property
    def amount(self):
        return (self.quantity * self.package.position.unit_price).quantize(Decimal("0.01"))
