"""Нейтральный модуль чтения и валидации текущих принятых ревизий отчётов MBG.

Не импортирует selectors.py или reporting_selectors.py во избежание циклических зависимостей.
Выполняет пакетную выборку текущих ревизий одним запросом без N+1 и сохраняет исходный
порядок переданных отчётов.
"""

from dataclasses import dataclass
from typing import Any, Sequence

from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils.translation import gettext as _

from .models import MbgDailyReport, MbgReportRevision


@dataclass(frozen=True)
class AcceptedRevisionBatch:
    items: tuple[tuple[MbgDailyReport, dict[str, Any]], ...]
    snapshots: tuple[dict[str, Any], ...]
    excluded_report_ids: tuple[int, ...]


def load_accepted_current_revisions(
    reports: Sequence[MbgDailyReport],
    *,
    strict: bool = False,
) -> AcceptedRevisionBatch:
    """Пакетно загрузить и валидировать текущие принятые ревизии для списка отчётов.

    Сохраняет точный исходный порядок входного списка отчётов (включая уже
    заблокированные через select_for_update).

    Валидирует:
    1. report.status == "accepted"
    2. ревизия для версии report.version существует
    3. snapshot['status'] == "accepted"

    При strict=True любое несоответствие вызывает ValidationError.
    При strict=False некорректные отчёты исключаются и их ID фиксируются в excluded_report_ids.
    """
    report_list = list(reports)
    if not report_list:
        return AcceptedRevisionBatch(items=(), snapshots=(), excluded_report_ids=())

    revisions_by_key = {
        (rev.report_id, rev.version): rev.snapshot
        for rev in MbgReportRevision.objects.filter(
            report__in=report_list,
            version=F("report__version"),
        ).only("report_id", "version", "snapshot")
    }

    items: list[tuple[MbgDailyReport, dict[str, Any]]] = []
    snapshots: list[dict[str, Any]] = []
    excluded_ids: list[int] = []

    for report in report_list:
        # 1. Проверка статуса отчёта
        if report.status != "accepted":
            if strict:
                raise ValidationError(
                    _("Отчёт %(id)s не утверждён (текущий статус: %(status)s)."),
                    params={"id": report.pk, "status": report.status},
                )
            excluded_ids.append(report.pk)
            continue

        # 2. Проверка наличия текущей ревизии
        snapshot = revisions_by_key.get((report.pk, report.version))
        if snapshot is None:
            if strict:
                raise ValidationError(
                    _("Отсутствует сохранённая ревизия версии %(version)s для отчёта %(id)s."),
                    params={"id": report.pk, "version": report.version},
                )
            excluded_ids.append(report.pk)
            continue

        # 3. Проверка статуса снимка
        if not isinstance(snapshot, dict) or snapshot.get("status") != "accepted":
            if strict:
                raise ValidationError(
                    _("Снимок версии %(version)s отчёта %(id)s не находится в статусе accepted."),
                    params={"id": report.pk, "version": report.version},
                )
            excluded_ids.append(report.pk)
            continue

        items.append((report, snapshot))
        snapshots.append(snapshot)

    return AcceptedRevisionBatch(
        items=tuple(items),
        snapshots=tuple(snapshots),
        excluded_report_ids=tuple(excluded_ids),
    )
