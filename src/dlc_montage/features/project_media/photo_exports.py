"""Prepare a bounded private ZIP of original photographs, without Nextcloud."""

import re
from tempfile import SpooledTemporaryFile
from time import monotonic
from zipfile import ZIP_STORED, ZipFile

from django.core.exceptions import ValidationError
from django.utils.translation import get_language

from .models import SitePhoto


def _message(ru, de):
    return ru if (get_language() or "").startswith("ru") else de


def build_photo_archive(site):
    """Stream originals into a private temporary file and close it on failure."""
    photos = list(SitePhoto.objects.filter(site=site))
    if not photos:
        raise ValidationError(_message("Нет фотографий для скачивания.", "Keine Fotos zum Herunterladen vorhanden."))
    if len(photos) > 200 or sum(photo.size for photo in photos) > 100 * 1024 * 1024:
        raise ValidationError(
            _message(
                "Архив превышает лимит 100 МБ или 200 фотографий. Скачайте оригиналы отдельно.",
                "Das Archiv überschreitet 100 MB oder 200 Fotos. Laden Sie die Originale einzeln herunter.",
            )
        )
    output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    deadline = monotonic() + 25
    total = 0
    try:
        with ZipFile(output, "w", compression=ZIP_STORED) as archive:
            for photo in photos:
                name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", photo.original_name).strip(" .")
                with photo.image.open("rb") as source, archive.open(f"{photo.pk}-{name or 'photo'}", "w") as target:
                    while chunk := source.read(64 * 1024):
                        total += len(chunk)
                        if total > 100 * 1024 * 1024 or monotonic() >= deadline:
                            raise ValidationError(
                                _message(
                                    "Не удалось подготовить архив вовремя. Скачайте оригиналы отдельно.",
                                    "Das Archiv konnte nicht rechtzeitig erstellt werden. "
                                    "Laden Sie die Originale einzeln herunter.",
                                )
                            )
                        target.write(chunk)
        output.seek(0)
        return output
    except Exception:
        output.close()
        raise
