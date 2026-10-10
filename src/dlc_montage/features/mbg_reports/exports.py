"""Явный фасад для экспорта отчётов MBG.

Содержит только реэкспорт сфокусированных модулей:
- export_workbooks: рендеринг Excel-книг и корпоративное оформление DLC Montage;
- export_services: бизнес-сценарии формирования отчётов и транзакции;
- export_storage: сохранение артефактов и очистка файлов при сбоях.
"""

from .export_services import (
    generate_final_hours,
    generate_performance_report,
    generate_site_performance_report,
    generate_week,
    generate_work_completion_report,
)
from .export_workbooks import (
    build_final_hourly_workbook,
    build_performance_workbook,
    build_weekly_workbook,
    build_work_completion_workbook,
    build_workbook,
)

__all__ = [
    "build_final_hourly_workbook",
    "build_performance_workbook",
    "build_weekly_workbook",
    "build_work_completion_workbook",
    "build_workbook",
    "generate_final_hours",
    "generate_performance_report",
    "generate_site_performance_report",
    "generate_week",
    "generate_work_completion_report",
]
