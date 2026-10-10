"""Хранение отчётов MBG с очисткой файла при ошибке сохранения модели.

Файловое хранилище не участвует в транзакции базы данных.
"""

from django.core.files.base import ContentFile

from .models import FinalHourlyExport, PerformanceExport, WeeklyExport


def store_export_artifact(artifact, content: bytes):
    """Сохранить сгенерированный Excel в файл артефакта с очисткой при ошибке сохранения модели."""
    artifact.file.save(artifact.filename, ContentFile(content), save=False)
    try:
        artifact.save()
    except Exception:
        artifact.file.delete(save=False)
        raise
    return artifact


def find_existing_weekly_export(fingerprint: str) -> WeeklyExport | None:
    """Найти ранее сохранённый недельный экспорт по отпечатку."""
    return WeeklyExport.objects.filter(fingerprint=fingerprint).first()


def find_existing_final_hourly_export(fingerprint: str) -> FinalHourlyExport | None:
    """Найти ранее сохранённый итоговый почасовой экспорт по отпечатку."""
    return FinalHourlyExport.objects.filter(fingerprint=fingerprint).first()


def find_existing_performance_export(fingerprint: str, document_type: str | None = None) -> PerformanceExport | None:
    """Найти ранее сохранённый экспорт выполненных работ по отпечатку."""
    queryset = PerformanceExport.objects.filter(fingerprint=fingerprint)
    if document_type is not None:
        queryset = queryset.filter(document_type=document_type)
    return queryset.first()
